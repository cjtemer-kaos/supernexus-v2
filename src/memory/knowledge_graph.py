"""
KnowledgeGraph - Grafo de conocimiento con memoria persistente y autopoda
Backend: SQLite (WAL + FTS5) + NetworkX opcional.
Fusiona: Ebbinghaus decay, Hebbian co-access, intent_meta, FTS5 full-text.

Características:
- Estado epistémico (draft/validated/outdated)
- Aristas semánticas tipadas (CAUSES, MITIGATES, FIXED_BY, etc.)
- intent_meta (why_connected + cognitive_pattern)
- Decaimiento Ebbinghaus (half-life por edge type)
- Auto-conexión Hebbiana (threshold=3)
- Poda automática (dry_run soportado)
- FTS5 full-text search (BM25-ranking)
- NetworkX opcional (centrality, community, Dijkstra)
- WAL mode + atomic transactions
"""

import logging
import json
import math
import sqlite3
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

EPISTEMIC_STATUSES = ("draft", "validated", "outdated")

EDGE_SEMANTIC_TYPES = (
    "RELATED_TO", "CAUSES", "MITIGATES", "FIXED_BY", "VIOLATED_BY",
    "CONTAINS", "EXEMPLIFIES", "DEPENDS_ON", "CONTRADICTS", "EXTENDS",
    "PARENT_OF", "CHILD_OF", "REFERENCES", "IMPLEMENTS", "GENERATES",
)

DEFAULT_HALF_LIFE_HOURS = {
    "RELATED_TO": 720, "CAUSES": 2160, "MITIGATES": 2160,
    "FIXED_BY": 4320, "VIOLATED_BY": 2160, "CONTAINS": 1440,
    "EXEMPLIFIES": 2160, "DEPENDS_ON": 4320, "CONTRADICTS": 2160,
    "EXTENDS": 1440, "PARENT_OF": 4320, "CHILD_OF": 4320,
    "REFERENCES": 720, "IMPLEMENTS": 2160, "GENERATES": 1440,
}

HEBBIAN_THRESHOLD = 3


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str
    content: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict = field(default_factory=dict)
    epistemic_status: str = "draft"
    access_count: int = 0
    last_access: str = ""

    def touch(self):
        self.access_count += 1
        self.last_access = datetime.now().isoformat()

    def promote(self) -> bool:
        if self.epistemic_status == "draft" and self.access_count >= 5:
            self.epistemic_status = "validated"
            return True
        return False

    def mark_outdated(self):
        self.epistemic_status = "outdated"

    @property
    def is_stale(self) -> bool:
        if self.epistemic_status == "outdated":
            return True
        if not self.last_access:
            return False
        try:
            last = datetime.fromisoformat(self.last_access)
            return (datetime.now() - last).days > 90 and self.access_count == 0
        except (ValueError, TypeError):
            return False


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str = "RELATED_TO"
    weight: float = 1.0
    description: str = ""
    half_life_hours: float = 720.0
    created_at: str = ""
    last_traversed: str = ""
    access_count: int = 0
    why_connected: str = ""
    cognitive_pattern: str = ""

    def touch(self):
        self.access_count += 1
        self.last_traversed = datetime.now().isoformat()
        self._recompute_weight()

    def _recompute_weight(self):
        age = self._age_hours()
        if age <= 0:
            return
        decay = math.exp(-math.log(2) * age / self.half_life_hours)
        boost = 1.0 + 0.1 * math.log1p(self.access_count)
        self.weight = max(0.01, min(1.0, decay * boost))

    def _age_hours(self) -> float:
        try:
            return (datetime.now() - datetime.fromisoformat(self.created_at)).total_seconds() / 3600.0
        except (ValueError, TypeError):
            return 0.0

    @property
    def is_decayed(self) -> bool:
        return self.weight < 0.05

    @property
    def is_stale(self) -> bool:
        if self.is_decayed:
            return True
        if not self.last_traversed:
            return False
        try:
            last = datetime.fromisoformat(self.last_traversed)
            return (datetime.now() - last).days > 180 and self.access_count == 0
        except (ValueError, TypeError):
            return False

    def set_intent(self, why: str = "", pattern: str = ""):
        self.why_connected = why
        self.cognitive_pattern = pattern


class KnowledgeGraph:
    """
    Grafo de conocimiento con memoria persistente (SQLite), decaimiento y autopoda.
    API compatible con la versión JSON anterior.

    Uso:
        graph = KnowledgeGraph()
        graph.add_node("py", "Python", "concept")
        graph.add_edge("py", "fastapi", "IMPLEMENTS",
                       why_connected="FastAPI está escrito en Python")
        graph.traverse_edge("py", "fastapi")
        stale = graph.prune()
        graph.create_note(category="research", name="tema", content="...")
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.db_path = Path(storage_path)
        else:
            self.db_path = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_graph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._co_access: Dict[Tuple[str, str], int] = defaultdict(int)
        self._init_db()
        self._load_cache()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                node_type TEXT NOT NULL DEFAULT 'concept',
                content TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                source TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL REFERENCES graph_nodes(id),
                target TEXT NOT NULL REFERENCES graph_nodes(id),
                edge_type TEXT NOT NULL DEFAULT 'RELATED_TO',
                weight REAL DEFAULT 1.0,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                links TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ge_source ON graph_edges(source);
            CREATE INDEX IF NOT EXISTS idx_ge_target ON graph_edges(target);
            CREATE INDEX IF NOT EXISTS idx_gn_type ON graph_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_gnote_cat ON graph_notes(category);
        """)
        for table, col, col_type in [
            ("graph_nodes", "epistemic_status", "TEXT DEFAULT 'draft'"),
            ("graph_nodes", "access_count", "INTEGER DEFAULT 0"),
            ("graph_nodes", "last_access", "TEXT DEFAULT ''"),
            ("graph_edges", "half_life_hours", "REAL DEFAULT 720.0"),
            ("graph_edges", "last_traversed", "TEXT DEFAULT ''"),
            ("graph_edges", "access_count", "INTEGER DEFAULT 0"),
            ("graph_edges", "why_connected", "TEXT DEFAULT ''"),
            ("graph_edges", "cognitive_pattern", "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gn_status ON graph_nodes(epistemic_status)")
        except Exception:
            pass
        # FTS5 full-text search
        try:
            conn.execute("DROP TABLE IF EXISTS graph_fts")
            conn.execute("""CREATE VIRTUAL TABLE graph_fts USING fts5(
                node_id UNINDEXED, label, content, tags, tokenize='porter unicode61')""")
        except Exception:
            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS graph_fts USING fts5(node_id UNINDEXED, label, content, tags)")
            except Exception:
                pass
        conn.commit()
        conn.close()

    def _row_to_node(self, row) -> GraphNode:
        tags = []
        try:
            tags = json.loads(row[4]) if row[4] else []
        except Exception:
            tags = [row[4]] if row[4] else []
        meta = {}
        try:
            meta = json.loads(row[8]) if row[8] else {}
        except Exception:
            pass
        return GraphNode(
            id=row[0], label=row[1], node_type=row[2],
            content=row[3] or "", tags=tags,
            created_at=row[5] or "", updated_at=row[6] or "",
            metadata=meta,
        )

    def _node_row_sql(self) -> str:
        return ("SELECT n.id, n.label, n.node_type, n.content, n.tags, "
                "n.created_at, n.updated_at, n.metadata, "
                "COALESCE(n.epistemic_status,'draft'), "
                "COALESCE(n.access_count,0), COALESCE(n.last_access,'') "
                "FROM graph_nodes n")

    def _load_cache(self):
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self._co_access.clear()
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        c = conn.cursor()
        try:
            c.execute(self._node_row_sql())
            for row in c.fetchall():
                node = self._row_to_node(row)
                node.epistemic_status = row[8] or "draft"
                node.access_count = row[9] or 0
                node.last_access = row[10] or ""
                self.nodes[node.id] = node
            c.execute("SELECT source, target, edge_type, weight, description, "
                      "half_life_hours, created_at, last_traversed, access_count, "
                      "why_connected, cognitive_pattern FROM graph_edges")
            for row in c.fetchall():
                edge = GraphEdge(
                    source=row[0], target=row[1], edge_type=row[2] or "RELATED_TO",
                    weight=row[3] or 1.0, description=row[4] or "",
                    half_life_hours=row[5] or 720.0, created_at=row[6] or "",
                    last_traversed=row[7] or "", access_count=row[8] or 0,
                    why_connected=row[9] or "", cognitive_pattern=row[10] or "",
                )
                self.edges.append(edge)
                self.adjacency[edge.source].add(edge.target)
        except Exception as e:
            logger.warning(f"Cache load issue: {e}")
        conn.close()

    def add_node(self, node_id: str, label: str, node_type: str,
                 content: str = "", tags: Optional[List[str]] = None,
                 metadata: Optional[Dict] = None,
                 epistemic_status: str = "draft") -> GraphNode:
        if epistemic_status not in EPISTEMIC_STATUSES:
            epistemic_status = "draft"
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        c = conn.cursor()
        c.execute("SELECT id FROM graph_nodes WHERE id=?", (node_id,))
        if c.fetchone():
            c.execute("""UPDATE graph_nodes SET label=?, node_type=?, updated_at=?,
                         epistemic_status=?, metadata=? WHERE id=?""",
                      (label, node_type, now, epistemic_status, meta_json, node_id))
            if content:
                c.execute("UPDATE graph_nodes SET content=? WHERE id=?", (content, node_id))
            if tags:
                c.execute("UPDATE graph_nodes SET tags=? WHERE id=?", (tags_json, node_id))
        else:
            c.execute("""INSERT INTO graph_nodes (id, label, node_type, content, tags,
                         created_at, updated_at, metadata, epistemic_status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (node_id, label, node_type, content, tags_json, now, now, meta_json, epistemic_status))
        conn.commit()
        conn.close()
        node = GraphNode(id=node_id, label=label, node_type=node_type, content=content,
                         tags=tags or [], created_at=now, updated_at=now,
                         metadata=metadata or {}, epistemic_status=epistemic_status)
        self.nodes[node_id] = node
        logger.debug(f"Node added: {node_id} ({label}) [{epistemic_status}]")
        return node

    def remove_node(self, node_id: str):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("DELETE FROM graph_edges WHERE source=? OR target=?", (node_id, node_id))
        conn.execute("DELETE FROM graph_nodes WHERE id=?", (node_id,))
        conn.commit()
        conn.close()
        if node_id in self.nodes:
            del self.nodes[node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        if node_id in self.adjacency:
            del self.adjacency[node_id]
        for src in self.adjacency:
            self.adjacency[src].discard(node_id)
        self._co_access = {pair: c for pair, c in self._co_access.items() if node_id not in pair}

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        node = self.nodes.get(node_id)
        if node:
            node.touch()
            self._update_node_db(node_id, node.access_count, node.last_access)
        return node

    def _update_node_db(self, node_id: str, access_count: int, last_access: str):
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            conn.execute("UPDATE graph_nodes SET access_count=?, last_access=? WHERE id=?",
                         (access_count, last_access, node_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def add_edge(self, source: str, target: str, edge_type: str = "RELATED_TO",
                 weight: Optional[float] = None, description: str = "",
                 half_life_hours: Optional[float] = None,
                 why_connected: str = "", cognitive_pattern: str = "") -> Optional[GraphEdge]:
        if source not in self.nodes or target not in self.nodes:
            logger.warning(f"Cannot add edge: node(s) not found ({source} -> {target})")
            return None
        if edge_type not in EDGE_SEMANTIC_TYPES:
            logger.warning(f"Unknown edge type '{edge_type}', defaulting to RELATED_TO")
            edge_type = "RELATED_TO"
        if weight is None:
            weight = 1.0
        if half_life_hours is None:
            half_life_hours = DEFAULT_HALF_LIFE_HOURS.get(edge_type, 720.0)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        c = conn.cursor()
        c.execute("SELECT id FROM graph_edges WHERE source=? AND target=? AND edge_type=?",
                  (source, target, edge_type))
        if c.fetchone():
            c.execute("""UPDATE graph_edges SET weight=MAX(weight,?), description=CASE WHEN ?!='' THEN ? ELSE description END,
                         why_connected=CASE WHEN ?!='' THEN ? ELSE why_connected END,
                         cognitive_pattern=CASE WHEN ?!='' THEN ? ELSE cognitive_pattern END
                         WHERE source=? AND target=? AND edge_type=?""",
                      (weight, description, description, why_connected, why_connected,
                       cognitive_pattern, cognitive_pattern, source, target, edge_type))
        else:
            c.execute("""INSERT INTO graph_edges (source, target, edge_type, weight, description,
                         created_at, half_life_hours, last_traversed, why_connected, cognitive_pattern)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (source, target, edge_type, weight, description[:200],
                       now, half_life_hours, now, why_connected[:200], cognitive_pattern[:100]))
            self.adjacency[source].add(target)
        conn.commit()
        conn.close()
        edge = GraphEdge(source=source, target=target, edge_type=edge_type,
                         weight=weight, description=description,
                         half_life_hours=half_life_hours, created_at=now,
                         why_connected=why_connected, cognitive_pattern=cognitive_pattern)
        self.edges.append(edge)
        logger.debug(f"Edge added: {source} --[{edge_type}]--> {target}")
        return edge

    def traverse_edge(self, source: str, target: str) -> Optional[GraphEdge]:
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                edge.touch()
                if source in self.nodes:
                    self.nodes[source].touch()
                    self._update_node_db(source, self.nodes[source].access_count, self.nodes[source].last_access)
                if target in self.nodes:
                    self.nodes[target].touch()
                    self._update_node_db(target, self.nodes[target].access_count, self.nodes[target].last_access)
                conn = sqlite3.connect(str(self.db_path), timeout=10)
                conn.execute("""UPDATE graph_edges SET access_count=?, last_traversed=?,
                                weight=? WHERE source=? AND target=?""",
                             (edge.access_count, edge.last_traversed, round(edge.weight, 3), source, target))
                conn.commit()
                conn.close()
                return edge
        return None

    def record_co_access(self, node_a: str, node_b: str):
        if node_a not in self.nodes or node_b not in self.nodes:
            return
        pair = tuple(sorted((node_a, node_b)))
        self._co_access[pair] += 1
        if self._co_access[pair] >= HEBBIAN_THRESHOLD:
            exists = any(
                (e.source == node_a and e.target == node_b) or
                (e.source == node_b and e.target == node_a)
                for e in self.edges
            )
            if not exists:
                self.add_edge(
                    node_a, node_b, "RELATED_TO",
                    why_connected=f"Hebbian co-access: {self._co_access[pair]} veces",
                    cognitive_pattern="co_access",
                )
                logger.info(f"Hebbian edge: {node_a} <-> {node_b}")

    def add_backlink(self, source: str, target: str, description: str = "", why_connected: str = ""):
        self.add_edge(source, target, "REFERENCES", description=description,
                      why_connected=why_connected or f"Backlink: {source} refiere a {target}")
        self.add_edge(target, source, "REFERENCES", description=description,
                      why_connected=why_connected or f"Backlink: {target} refiere a {source}")

    def find_related(self, node_id: str, max_depth: int = 2, min_weight: float = 0.1) -> Dict[str, GraphNode]:
        if node_id not in self.nodes:
            return {}
        visited = set()
        queue = [(node_id, 0)]
        related = {}
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            if current_id != node_id and current_id in self.nodes:
                related[current_id] = self.nodes[current_id]
            for neighbor in self.adjacency.get(current_id, set()):
                if neighbor not in visited:
                    ew = self._get_edge_weight(current_id, neighbor)
                    if ew is None or ew >= min_weight:
                        queue.append((neighbor, depth + 1))
        return related

    def _get_edge_weight(self, source: str, target: str) -> Optional[float]:
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge.weight
        return None

    def find_path(self, source: str, target: str, min_weight: float = 0.1) -> Optional[List[str]]:
        if source not in self.nodes or target not in self.nodes:
            return None
        visited = {source}
        queue = [(source, [source])]
        while queue:
            current, path = queue.pop(0)
            if current == target:
                return path
            for neighbor in self.adjacency.get(current, set()):
                if neighbor not in visited:
                    ew = self._get_edge_weight(current, neighbor)
                    if ew is not None and ew >= min_weight:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
        return None

    def search_by_intent(self, why_pattern: str) -> List[Dict]:
        results = []
        for edge in self.edges:
            if why_pattern.lower() in edge.why_connected.lower():
                results.append({
                    "source": edge.source, "target": edge.target,
                    "edge_type": edge.edge_type, "why_connected": edge.why_connected,
                    "cognitive_pattern": edge.cognitive_pattern, "weight": edge.weight,
                })
        return results

    def get_decayed_edges(self, threshold: float = 0.05) -> List[GraphEdge]:
        return [e for e in self.edges if e.weight < threshold]

    def prune(self, dry_run: bool = False) -> Dict:
        removed_edges_data = []
        removed_nodes_data = []
        stale_edges = [e for e in self.edges if e.is_stale]
        for edge in stale_edges:
            removed_edges_data.append({
                "source": edge.source, "target": edge.target,
                "type": edge.edge_type, "weight": edge.weight, "reason": "stale_or_decayed",
            })
            if not dry_run:
                self.edges.remove(edge)
                self.adjacency[edge.source].discard(edge.target)
        stale_nodes = [nid for nid, node in self.nodes.items() if node.is_stale]
        for nid in stale_nodes:
            node = self.nodes[nid]
            removed_nodes_data.append({"id": nid, "label": node.label, "status": node.epistemic_status, "reason": "stale"})
            if not dry_run:
                self.remove_node(nid)
        if not dry_run and (stale_edges or stale_nodes):
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            for e in stale_edges:
                conn.execute("DELETE FROM graph_edges WHERE source=? AND target=? AND edge_type=?",
                             (e.source, e.target, e.edge_type))
            conn.commit()
            conn.close()
            self._load_cache()
        total = len(removed_edges_data) + len(removed_nodes_data)
        if total > 0:
            logger.info(f"Pruned {len(removed_nodes_data)} nodes + {len(removed_edges_data)} edges")
        return {
            "dry_run": dry_run,
            "removed_nodes": len(removed_nodes_data),
            "removed_edges": len(removed_edges_data),
            "nodes_remaining": len(self.nodes),
            "edges_remaining": len(self.edges),
            "detail_nodes": removed_nodes_data[:20],
            "detail_edges": removed_edges_data[:20],
        }

    def consolidate_epistemic_status(self):
        promoted = 0
        for node in self.nodes.values():
            if node.promote():
                promoted += 1
        if promoted:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            conn.execute("UPDATE graph_nodes SET epistemic_status='validated' WHERE id=?",
                         tuple(n.id for n in self.nodes.values() if n.epistemic_status == "validated"))
            conn.commit()
            conn.close()
            logger.info(f"Promoted {promoted} nodes from draft to validated")

    def analyze_dependencies(self, node_id: str) -> Dict:
        if node_id not in self.nodes:
            return {"error": "Node not found"}
        incoming = [e for e in self.edges if e.target == node_id]
        outgoing = [e for e in self.edges if e.source == node_id]
        related = self.find_related(node_id)
        return {
            "node": self.nodes[node_id].label,
            "epistemic_status": self.nodes[node_id].epistemic_status,
            "access_count": self.nodes[node_id].access_count,
            "incoming_dependencies": len(incoming),
            "outgoing_dependencies": len(outgoing),
            "total_related": len(related),
            "related_nodes": list(related.keys()),
        }

    def get_central_nodes(self, top_n: int = 10) -> List[Dict]:
        counts = defaultdict(int)
        for edge in self.edges:
            if edge.weight >= 0.05:
                counts[edge.source] += 1
                counts[edge.target] += 1
        sorted_nodes = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"id": nid, "label": self.nodes[nid].label if nid in self.nodes else "?",
             "epistemic_status": self.nodes[nid].epistemic_status if nid in self.nodes else "?",
             "connections": cnt}
            for nid, cnt in sorted_nodes[:top_n] if nid in self.nodes
        ]

    def get_stats(self) -> Dict:
        node_types = defaultdict(int)
        status_counts = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1
            status_counts[node.epistemic_status] += 1
        edge_types = defaultdict(int)
        decayed_count = 0
        for edge in self.edges:
            edge_types[edge.edge_type] += 1
            if edge.is_decayed:
                decayed_count += 1
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            c = conn.cursor()
            c.execute("SELECT category, COUNT(*) FROM graph_notes GROUP BY category")
            by_category = dict(c.fetchall())
        except Exception:
            by_category = {}
        conn.close()
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "epistemic_status": dict(status_counts),
            "decayed_edges": decayed_count,
            "hebbian_pairs": len(self._co_access),
            "avg_connections": (len(self.edges) * 2 / len(self.nodes)) if self.nodes else 0,
            "by_category": by_category,
        }

    def export_for_visualization(self, min_weight: float = 0.0) -> Dict:
        nodes_data = [
            {"id": node.id, "label": node.label, "type": node.node_type,
             "tags": node.tags, "epistemic_status": node.epistemic_status,
             "access_count": node.access_count, "metadata": node.metadata}
            for node in self.nodes.values()
        ]
        edges_data = [
            {"source": edge.source, "target": edge.target, "type": edge.edge_type,
             "weight": round(edge.weight, 3), "description": edge.description,
             "why_connected": edge.why_connected, "cognitive_pattern": edge.cognitive_pattern}
            for edge in self.edges if edge.weight >= min_weight
        ]
        return {"nodes": nodes_data, "edges": edges_data, "stats": self.get_stats()}

    # --- Notes API (compatibilidad con aprendizaje) ---

    def create_note(self, category: str, name: str, content: str = "",
                    tags: Optional[List[str]] = None, links: Optional[List[str]] = None) -> Dict:
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        links_json = json.dumps(links or [], ensure_ascii=False)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("""INSERT INTO graph_notes (category, name, content, tags, links, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (category, name, content, tags_json, links_json, now, now))
        conn.commit()
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        # También crear nodo en el grafo
        self.add_node(f"note:{note_id}", name, "note", content=content, tags=tags)
        logger.info(f"Note created: {category}/{name}")
        return {"id": note_id, "category": category, "name": name, "success": True}

    def list_notes(self, category: Optional[str] = None) -> Dict:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        c = conn.cursor()
        if category:
            c.execute("SELECT id, category, name, content, tags, links, created_at FROM graph_notes WHERE category=? ORDER BY id DESC", (category,))
        else:
            c.execute("SELECT id, category, name, content, tags, links, created_at FROM graph_notes ORDER BY id DESC")
        notes = []
        for row in c.fetchall():
            tags, links = [], []
            try:
                tags = json.loads(row[4]) if row[4] else []
            except Exception:
                pass
            try:
                links = json.loads(row[5]) if row[5] else []
            except Exception:
                pass
            notes.append({
                "id": row[0], "category": row[1], "title": row[2],
                "content": row[3], "tags": tags, "links": links,
                "created_at": row[6],
            })
        conn.close()
        return {"notes": notes}

    # --- FTS5 Full-Text Search (BM25-ranking) ---

    def fts_rebuild(self):
        """Reconstruye el índice FTS5 desde los nodos actuales."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("DELETE FROM graph_fts")
        c = conn.cursor()
        count = 0
        for nid, node in self.nodes.items():
            tags_str = " ".join(node.tags) if node.tags else ""
            try:
                c.execute("INSERT INTO graph_fts (node_id, label, content, tags) VALUES (?, ?, ?, ?)",
                          (nid, node.label, node.content[:5000], tags_str))
                count += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        logger.info(f"FTS rebuilt: {count} documents indexed")
        return count

    def fts_search(self, query: str, limit: int = 20) -> List[Dict]:
        """Búsqueda full-text con ranking BM25."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        c = conn.cursor()
        safe_query = " OR ".join(f'"{w}"' if " " in w else w for w in query.split())
        try:
            c.execute(
                "SELECT node_id, label, content, tags, rank FROM graph_fts WHERE graph_fts MATCH ? ORDER BY rank LIMIT ?",
                (safe_query, limit),
            )
            results = []
            for row in c.fetchall():
                tags = row[3].split() if row[3] else []
                results.append({
                    "node_id": row[0], "label": row[1],
                    "content": row[2][:500] if row[2] else "",
                    "tags": tags, "rank": round(row[4], 4),
                })
        except Exception as e:
            logger.warning(f"FTS search failed: {e}")
            results = []
            # fallback LIKE search
            like = f"%{query}%"
            try:
                c.execute("SELECT id, label, content, tags FROM graph_nodes WHERE label LIKE ? OR content LIKE ? LIMIT ?",
                          (like, like, limit))
                for row in c.fetchall():
                    tags = json.loads(row[3]) if row[3] else []
                    results.append({"node_id": row[0], "label": row[1], "content": row[2][:500], "tags": tags, "rank": 0})
            except Exception:
                pass
        conn.close()
        return results

    # --- NetworkX Integration (opcional) ---

    def to_networkx(self):
        """Convierte el grafo a NetworkX DiGraph (requiere pip install networkx)."""
        import networkx as nx
        G = nx.DiGraph()
        for nid, node in self.nodes.items():
            G.add_node(nid, label=node.label, type=node.node_type,
                       epistemic_status=node.epistemic_status, access_count=node.access_count)
        for edge in self.edges:
            if edge.weight >= 0.05:
                G.add_edge(edge.source, edge.target, weight=edge.weight,
                           edge_type=edge.edge_type, why_connected=edge.why_connected)
        return G

    def centrality(self, top_n: int = 10) -> List[Dict]:
        """PageRank centrality via NetworkX (no-op si no está instalado)."""
        try:
            import networkx as nx
            G = self.to_networkx()
            pr = nx.pagerank(G, weight="weight")
            sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_n]
            return [{"id": nid, "label": self.nodes[nid].label if nid in self.nodes else "?",
                     "pagerank": round(score, 4), "connections": G.degree(nid)}
                    for nid, score in sorted_pr]
        except ImportError:
            logger.warning("networkx not installed, falling back to degree centrality")
            return self.get_central_nodes(top_n)

    def shortest_path(self, source: str, target: str) -> Optional[Dict]:
        """Dijkstra shortest path via NetworkX."""
        try:
            import networkx as nx
            G = self.to_networkx()
            path = nx.shortest_path(G, source=source, target=target, weight="weight")
            length = nx.shortest_path_length(G, source=source, target=target, weight="weight")
            path_info = []
            for i in range(len(path) - 1):
                for edge in self.edges:
                    if edge.source == path[i] and edge.target == path[i + 1]:
                        path_info.append({"source": path[i], "target": path[i + 1],
                                          "edge_type": edge.edge_type, "weight": edge.weight})
                        break
            return {"path": path, "length": round(length, 3), "edges": path_info, "nodes": len(path)}
        except (ImportError, nx.NetworkXNoPath, nx.NodeNotFound) as e:
            return {"error": str(e)}

    def community_detection(self) -> List[Dict]:
        """Detección de comunidades vía greedy modularity (NetworkX)."""
        try:
            import networkx as nx
            import networkx.algorithms.community as nxcom
            G = self.to_networkx()
            communities = list(nxcom.greedy_modularity_communities(G.to_undirected(), weight="weight"))
            result = []
            for i, comm in enumerate(communities[:20]):
                members = [{"id": n, "label": self.nodes[n].label if n in self.nodes else "?"} for n in comm]
                result.append({"community_id": i, "size": len(comm), "members": members[:10]})
            return result
        except ImportError:
            return [{"error": "networkx not installed"}]

    # --- Backward compat: save/load son no-ops (SQLite escribe en vivo) ---

    def save(self):
        pass

    def load(self):
        self._load_cache()
