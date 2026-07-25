"""
Knowledge Graph — SQLite graph + FTS5 + entity linking for Nexus brain.

Replaces the flat "conocimientos" table with a proper graph:
  - Nodes: concepts, facts, lessons, patterns (each with embedding-ready text)
  - Edges: typed relations (relates_to, supersedes, contradicts, derived_from, etc.)
  - Entities: extracted entities linked to nodes for cross-reference boosting
  - FTS5: full-text search on node content + entity names

Inspired by: Lethe (archival memory), Mem0 (entity linking + ADD-only), Graphify (graph analysis).

Migration: reads existing cerebro.db conocimientos, extracts entities, builds graph.
"""

import json
import re
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".nexus" / "brain" / "knowledge_graph.db"


# =============================================================================
# Data models
# =============================================================================

@dataclass
class KNode:
    """A knowledge node (concept, fact, lesson, pattern)."""
    id: Optional[int] = None
    content: str = ""
    title: str = ""
    category: str = "general"  # general, lesson, pattern, fact, decision, config
    source: str = "nexus"  # which agent created it
    importance: int = 5  # 1-10
    tags: List[str] = field(default_factory=list)
    content_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0
    last_accessed: str = ""
    # Computed
    entity_count: int = 0
    edge_count: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = json.dumps(d["tags"])
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "KNode":
        return cls(
            id=row["id"],
            content=row["content"],
            title=row["title"],
            category=row["category"],
            source=row["source"],
            importance=row["importance"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            access_count=row["access_count"],
            last_accessed=row["last_accessed"] or "",
        )


@dataclass
class KEdge:
    """A typed edge between two knowledge nodes."""
    id: Optional[int] = None
    from_node: int = 0
    to_node: int = 0
    relation: str = "relates_to"  # relates_to, supersedes, contradicts, derived_from, part_of, enables
    weight: float = 1.0
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "KEdge":
        return cls(
            id=row["id"],
            from_node=row["from_node"],
            to_node=row["to_node"],
            relation=row["relation"],
            weight=row["weight"],
            note=row["note"],
            created_at=row["created_at"],
        )


@dataclass
class KEntity:
    """An extracted entity linked to one or more nodes."""
    id: Optional[int] = None
    name: str = ""
    entity_type: str = "concept"  # concept, file, function, tool, url, person, project
    node_ids: List[int] = field(default_factory=list)
    mention_count: int = 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["node_ids"] = json.dumps(d["node_ids"])
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "KEntity":
        return cls(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            node_ids=json.loads(row["node_ids"]) if row["node_ids"] else [],
            mention_count=row["mention_count"],
        )


# =============================================================================
# Entity extraction (lightweight, no LLM needed)
# =============================================================================

# Patterns for entity extraction
_ENTITY_PATTERNS = {
    "file": re.compile(r"[\w/._-]+\.(?:py|js|ts|json|yaml|yml|md|sql|db|toml)"),
    "url": re.compile(r"https?://[^\s]+"),
    "function": re.compile(r"\b(?:def|function|class)\s+(\w+)"),
    "tool": re.compile(r"\b(?:pip|npm|docker|curl|git|pytest|node|python)\s+\w+"),
}


def _extract_entities(text: str) -> List[Tuple[str, str]]:
    """Extract entities from text. Returns [(name, type), ...]."""
    entities = []
    seen = set()

    # Extract files
    for m in _ENTITY_PATTERNS["file"].finditer(text):
        name = m.group(0).strip()
        if name not in seen and len(name) > 3:
            entities.append((name, "file"))
            seen.add(name)

    # Extract URLs
    for m in _ENTITY_PATTERNS["url"].finditer(text):
        name = m.group(0).rstrip(".,)")
        if name not in seen:
            entities.append((name, "url"))
            seen.add(name)

    # Extract function/class names
    for m in _ENTITY_PATTERNS["function"].finditer(text):
        name = m.group(1)
        if name not in seen and len(name) > 2:
            entities.append((name, "function"))
            seen.add(name)

    # Extract tools
    for m in _ENTITY_PATTERNS["tool"].finditer(text):
        name = m.group(0).strip()
        if name not in seen:
            entities.append((name, "tool"))
            seen.add(name)

    # Extract capitalized terms (concepts) — simple heuristic
    words = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text)
    for w in words:
        if w not in seen and len(w) > 4 and w not in ("Http", "Https", "Json", "Url", "Sql", "Api"):
            entities.append((w, "concept"))
            seen.add(w)

    return entities


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# KnowledgeGraph — the main class
# =============================================================================

class KnowledgeGraph:
    """Graph-based knowledge store with FTS5 + entity linking.

    SQLite schema:
      nodes: id, content, title, category, source, importance, tags, content_hash,
             created_at, updated_at, access_count, last_accessed
      edges: id, from_node, to_node, relation, weight, note, created_at
      entities: id, name, entity_type, node_ids, mention_count
      nodes_fts: FTS5 virtual table on (title, content, tags, category)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_db(self):
        db = self._db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'general',
                source TEXT NOT NULL DEFAULT 'nexus',
                importance INTEGER NOT NULL DEFAULT 5,
                tags TEXT NOT NULL DEFAULT '[]',
                content_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                to_node INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                relation TEXT NOT NULL DEFAULT 'relates_to',
                weight REAL NOT NULL DEFAULT 1.0,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(from_node, to_node, relation)
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT 'concept',
                node_ids TEXT NOT NULL DEFAULT '[]',
                mention_count INTEGER NOT NULL DEFAULT 1,
                UNIQUE(name, entity_type)
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category);
            CREATE INDEX IF NOT EXISTS idx_nodes_source ON nodes(source);
            CREATE INDEX IF NOT EXISTS idx_nodes_importance ON nodes(importance);
            CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_node);
            CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_node);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        """)

        # FTS5 virtual table
        try:
            db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    title, content, tags, category,
                    content=nodes,
                    content_rowid=id
                )
            """)
        except sqlite3.OperationalError:
            pass  # already exists

        # Triggers to keep FTS in sync
        for trigger_sql in [
            """CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(rowid, title, content, tags, category)
                VALUES (new.id, new.title, new.content, new.tags, new.category);
            END""",
            """CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, title, content, tags, category)
                VALUES ('delete', old.id, old.title, old.content, old.tags, old.category);
            END""",
            """CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, title, content, tags, category)
                VALUES ('delete', old.id, old.title, old.content, old.tags, old.category);
                INSERT INTO nodes_fts(rowid, title, content, tags, category)
                VALUES (new.id, new.title, new.content, new.tags, new.category);
            END""",
        ]:
            try:
                db.execute(trigger_sql)
            except sqlite3.OperationalError:
                pass

        db.commit()

    # -------------------------------------------------------------------------
    # CRUD — Nodes
    # -------------------------------------------------------------------------

    def add_node(self, content: str, title: str = "", category: str = "general",
                 source: str = "nexus", importance: int = 5, tags: Optional[List[str]] = None,
                 do_extract_entities: bool = True) -> int:
        """Add a knowledge node. Returns node ID."""
        now = datetime.now(timezone.utc).isoformat()
        content_hash = compute_hash(content)
        if not title:
            title = content[:80].replace("\n", " ")

        db = self._db()
        cur = db.execute(
            """INSERT INTO nodes (content, title, category, source, importance, tags,
               content_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (content, title, category, source, importance,
             json.dumps(tags or []), content_hash, now, now)
        )
        node_id = cur.lastrowid

        # Extract and link entities
        if do_extract_entities:
            entities = _extract_entities(content + " " + title)
            for ent_name, ent_type in entities:
                self._link_entity(node_id, ent_name, ent_type)

        db.commit()
        logger.info(f"Node added: {node_id} ({category}) [{len(entities)} entities]")
        return node_id

    def get_node(self, node_id: int) -> Optional[KNode]:
        """Get a node by ID."""
        db = self._db()
        row = db.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row:
            # Update access count
            db.execute(
                "UPDATE nodes SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), node_id)
            )
            db.commit()
            return KNode.from_row(row)
        return None

    def update_node(self, node_id: int, content: Optional[str] = None,
                    title: Optional[str] = None, category: Optional[str] = None,
                    importance: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """Update a node. Returns True if updated."""
        db = self._db()
        now = datetime.now(timezone.utc).isoformat()
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
            updates.append("content_hash = ?")
            params.append(compute_hash(content))
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(now)
        params.append(node_id)

        db.execute(f"UPDATE nodes SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
        return True

    def delete_node(self, node_id: int) -> bool:
        """Delete a node and its edges."""
        db = self._db()
        db.execute("DELETE FROM edges WHERE from_node = ? OR to_node = ?", (node_id, node_id))
        cur = db.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        db.commit()
        return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # CRUD — Edges
    # -------------------------------------------------------------------------

    def add_edge(self, from_node: int, to_node: int, relation: str = "relates_to",
                 weight: float = 1.0, note: str = "") -> Optional[int]:
        """Add an edge between two nodes. Returns edge ID or None if duplicate."""
        now = datetime.now(timezone.utc).isoformat()
        db = self._db()
        try:
            cur = db.execute(
                """INSERT INTO edges (from_node, to_node, relation, weight, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (from_node, to_node, relation, weight, note, now)
            )
            db.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # duplicate edge

    def get_edges(self, node_id: int, direction: str = "both") -> List[KEdge]:
        """Get edges for a node. direction: 'out', 'in', 'both'."""
        db = self._db()
        edges = []
        if direction in ("out", "both"):
            for row in db.execute("SELECT * FROM edges WHERE from_node = ?", (node_id,)):
                edges.append(KEdge.from_row(row))
        if direction in ("in", "both"):
            for row in db.execute("SELECT * FROM edges WHERE to_node = ?", (node_id,)):
                edges.append(KEdge.from_row(row))
        return edges

    def delete_edge(self, from_node: int, to_node: int, relation: str = "relates_to") -> bool:
        db = self._db()
        cur = db.execute(
            "DELETE FROM edges WHERE from_node = ? AND to_node = ? AND relation = ?",
            (from_node, to_node, relation)
        )
        db.commit()
        return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Entity linking
    # -------------------------------------------------------------------------

    def _link_entity(self, node_id: int, name: str, entity_type: str):
        """Link an entity to a node. Creates or updates entity."""
        db = self._db()
        row = db.execute(
            "SELECT id, node_ids, mention_count FROM entities WHERE name = ? AND entity_type = ?",
            (name, entity_type)
        ).fetchone()

        if row:
            node_ids = json.loads(row["node_ids"])
            if node_id not in node_ids:
                node_ids.append(node_id)
            db.execute(
                "UPDATE entities SET node_ids = ?, mention_count = mention_count + 1 WHERE id = ?",
                (json.dumps(node_ids), row["id"])
            )
        else:
            db.execute(
                "INSERT INTO entities (name, entity_type, node_ids, mention_count) VALUES (?, ?, ?, 1)",
                (name, entity_type, json.dumps([node_id]))
            )

    def get_entity(self, name: str) -> Optional[KEntity]:
        db = self._db()
        row = db.execute("SELECT * FROM entities WHERE name = ?", (name,)).fetchone()
        return KEntity.from_row(row) if row else None

    def get_entities_for_node(self, node_id: int) -> List[KEntity]:
        """Get all entities linked to a node."""
        db = self._db()
        entities = []
        for row in db.execute("SELECT * FROM entities"):
            node_ids = json.loads(row["node_ids"])
            if node_id in node_ids:
                entities.append(KEntity.from_row(row))
        return entities

    def get_related_nodes(self, node_id: int) -> List[Tuple[KNode, KEdge]]:
        """Get nodes connected to this node (via edges)."""
        edges = self.get_edges(node_id)
        related = []
        for edge in edges:
            other_id = edge.to_node if edge.from_node == node_id else edge.from_node
            node = self.get_node(other_id)
            if node:
                related.append((node, edge))
        return related

    # -------------------------------------------------------------------------
    # Search — FTS5 + entity boosting
    # -------------------------------------------------------------------------

    def search(self, query: str, limit: int = 20, category: Optional[str] = None,
               boost_entities: bool = True) -> List[Dict]:
        """Full-text search with optional entity boosting.

        Returns list of {node, score, entities, edges}.
        """
        db = self._db()

        # FTS5 search
        fts_query = query.replace('"', '""')
        where_clause = ""
        params: list = []

        if category:
            where_clause = "AND n.category = ?"
            params.append(category)

        sql = f"""
            SELECT n.*, fts.rank
            FROM nodes_fts fts
            JOIN nodes n ON n.id = fts.rowid
            WHERE nodes_fts MATCH ?
            {where_clause}
            ORDER BY fts.rank
            LIMIT ?
        """
        params.insert(0, fts_query)
        params.append(limit)

        try:
            rows = db.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # Fallback to LIKE search
            sql = f"SELECT * FROM nodes n WHERE (n.title LIKE ? OR n.content LIKE ?) {where_clause} LIMIT ?"
            like_q = f"%{query}%"
            rows = db.execute(sql, [like_q, like_q] + params[1:]).fetchall()

        results = []
        for row in rows:
            node = KNode.from_row(row)
            score = abs(row["rank"]) if "rank" in row.keys() else 0
            entities = self.get_entities_for_node(node.id) if boost_entities else []
            edges = self.get_edges(node.id)
            results.append({
                "node": node,
                "score": score,
                "entities": entities,
                "edges": edges,
            })

        return results

    def search_by_entity(self, entity_name: str, limit: int = 20) -> List[KNode]:
        """Find all nodes linked to an entity."""
        db = self._db()
        row = db.execute(
            "SELECT node_ids FROM entities WHERE name = ?",
            (entity_name,)
        ).fetchone()
        if not row:
            return []

        node_ids = json.loads(row["node_ids"])
        nodes = []
        for nid in node_ids[:limit]:
            node = self.get_node(nid)
            if node:
                nodes.append(node)
        return nodes

    def auto_link(self, similarity_threshold: float = 0.3):
        """Auto-create edges between nodes that share entities.

        This is the entity-linking boost from mem0: nodes that mention
        the same entities are likely related.
        """
        db = self._db()
        entities = db.execute(
            "SELECT name, node_ids FROM entities WHERE mention_count > 1"
        ).fetchall()

        new_edges = 0
        for ent in entities:
            node_ids = json.loads(ent["node_ids"])
            # Connect all nodes that share this entity
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    result = self.add_edge(
                        node_ids[i], node_ids[j],
                        relation="relates_to",
                        weight=0.5,
                        note=f"shared entity: {ent['name']}"
                    )
                    if result:
                        new_edges += 1

        logger.info(f"Auto-linked: {new_edges} new edges from {len(entities)} shared entities")
        return new_edges

    # -------------------------------------------------------------------------
    # Migration from cerebro.db
    # -------------------------------------------------------------------------

    def migrate_from_cerebro(self, cerebro_path: Optional[str] = None):
        """Migrate conocimientos from old cerebro.db to the new graph."""
        src = Path(cerebro_path) if cerebro_path else Path.home() / ".nexus" / "brain" / "cerebro.db"
        if not src.exists():
            logger.warning(f"cerebro.db not found at {src}")
            return 0

        src_conn = sqlite3.connect(str(src))
        src_conn.row_factory = sqlite3.Row

        # Check what tables exist
        tables = [r[0] for r in src_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        count = 0
        if "conocimientos" in tables:
            for row in src_conn.execute("SELECT * FROM conocimientos"):
                row_dict = dict(row)
                content = row_dict.get("contenido", row_dict.get("content", ""))
                title = row_dict.get("topic", row_dict.get("titulo", content[:80]))
                category = row_dict.get("categoria", row_dict.get("category", "general"))
                importance = row_dict.get("importancia", row_dict.get("importance", 5))

                if content.strip():
                    self.add_node(
                        content=content,
                        title=title,
                        category=category,
                        source="cerebro_migration",
                        importance=importance,
                    )
                    count += 1

        src_conn.close()

        # Auto-link after migration
        if count > 0:
            self.auto_link()

        logger.info(f"Migrated {count} conocimientos from cerebro.db to knowledge graph")
        return count

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    def stats(self) -> Dict:
        db = self._db()
        node_count = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        entity_count = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        categories = {}
        for row in db.execute("SELECT category, COUNT(*) as cnt FROM nodes GROUP BY category"):
            categories[row["category"]] = row["cnt"]

        edge_types = {}
        for row in db.execute("SELECT relation, COUNT(*) as cnt FROM edges GROUP BY relation"):
            edge_types[row["relation"]] = row["cnt"]

        top_entities = []
        for row in db.execute(
            "SELECT name, entity_type, mention_count FROM entities ORDER BY mention_count DESC LIMIT 10"
        ):
            top_entities.append({"name": row["name"], "type": row["entity_type"], "mentions": row["mention_count"]})

        return {
            "nodes": node_count,
            "edges": edge_count,
            "entities": entity_count,
            "categories": categories,
            "edge_types": edge_types,
            "top_entities": top_entities,
            "db_size_kb": round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0,
        }

    def export_mermaid(self) -> str:
        """Export graph as Mermaid diagram."""
        db = self._db()
        lines = ["graph LR"]

        nodes = db.execute("SELECT id, title, category FROM nodes ORDER BY importance DESC LIMIT 50").fetchall()
        for n in nodes:
            safe_title = n["title"].replace('"', "'")[:40]
            lines.append(f'    {n["id"]}["{safe_title}"]')

        for row in db.execute("SELECT from_node, to_node, relation FROM edges LIMIT 80"):
            lines.append(f"    {row['from_node']} -->|{row['relation']}| {row['to_node']}")

        return "\n".join(lines)


# =============================================================================
# Singleton
# =============================================================================

_instance = None


def get_knowledge_graph(db_path: Optional[str] = None) -> KnowledgeGraph:
    global _instance
    if _instance is None:
        _instance = KnowledgeGraph(db_path)
    return _instance
