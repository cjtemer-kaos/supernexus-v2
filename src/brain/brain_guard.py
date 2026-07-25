"""
BrainGuard — anti-crecimiento para el Knowledge Graph.

Evita que knowledge_graph.db crezca descontroladamente:
1. Deduplication: nodes con contenido similar se fusionan
2. TTL: nodos viejos de baja importancia se archivan (no se borran)
3. Compression: nodos de baja importancia se comprimen
4. Pruning: auto-limpieza periódica
5. Limits: max nodes, max edges, max entities

Patrón inspirado en: Lethe (forgetting curves), Mem0 (dedup por hash).
"""

import sqlite3
import hashlib
import logging
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".nexus" / "brain" / "knowledge_graph.db"

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_NODES = 5000           # Límite duro de nodos
MAX_EDGES = 15000          # Límite duro de edges
MAX_ENTITIES = 3000        # Límite duro de entidades
TTL_DAYS_LOW_IMPORTANCE = 90   # Nodos < importance 4 se archivan después de 90 días
TTL_DAYS_GENERAL = 365         # Nodos generales se archivan después de 1 año
COMPRESS_THRESHOLD = 3         # Nodos con access_count < 3 se comprimen
MERGE_HASH_THRESHOLD = 0.95    # Similitud para fusionar nodos (Jaccard de palabras)


class BrainGuard:
    """Gestiona el tamaño del Knowledge Graph."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH

    def _db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ── 1. Deduplication ──────────────────────────────────────────────────────

    def _content_hash(self, text: str) -> str:
        """Hash normalizado de contenido para dedup."""
        normalized = " ".join(text.lower().split())[:500]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _word_set(self, text: str) -> set:
        """Set de palabras normalizado para Jaccard similarity."""
        return set(text.lower().split())

    def _jaccard(self, a: set, b: set) -> float:
        """Similitud Jaccard entre dos sets."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _merge_node(self, db: sqlite3.Connection, keep_id: int, dup_id: int):
        """Fusiona un nodo duplicado en keep, manejando edges duplicados."""
        # 1) Edges donde dup es source: si keep ya tiene ese edge, eliminar el de dup;
        #    si no, redirigir a keep.
        dup_src = db.execute(
            "SELECT id, to_node, relation, weight FROM edges WHERE from_node = ?", (dup_id,)
        ).fetchall()
        for e in dup_src:
            exists = db.execute(
                "SELECT id FROM edges WHERE from_node = ? AND to_node = ? AND relation = ?",
                (keep_id, e["to_node"], e["relation"])
            ).fetchone()
            if exists:
                # Edge ya existe en keep → eliminar el de dup, fusionar peso
                db.execute("UPDATE edges SET weight = weight + ? WHERE id = ?",
                           (e["weight"], exists["id"]))
                db.execute("DELETE FROM edges WHERE id = ?", (e["id"],))
            else:
                db.execute("UPDATE edges SET from_node = ? WHERE id = ?",
                           (keep_id, e["id"]))

        # 2) Edges donde dup es target
        dup_tgt = db.execute(
            "SELECT id, from_node, relation, weight FROM edges WHERE to_node = ?", (dup_id,)
        ).fetchall()
        for e in dup_tgt:
            exists = db.execute(
                "SELECT id FROM edges WHERE from_node = ? AND to_node = ? AND relation = ?",
                (e["from_node"], keep_id, e["relation"])
            ).fetchone()
            if exists:
                db.execute("UPDATE edges SET weight = weight + ? WHERE id = ?",
                           (e["weight"], exists["id"]))
                db.execute("DELETE FROM edges WHERE id = ?", (e["id"],))
            else:
                db.execute("UPDATE edges SET to_node = ? WHERE id = ?",
                           (keep_id, e["id"]))

        # 3) Redirigir entity_links (campo node_ids TEXT en tabla entities)
        dup_entities = db.execute(
            "SELECT id, node_ids FROM entities WHERE node_ids LIKE ?", (f'%{dup_id}%',)
        ).fetchall()
        for ent in dup_entities:
            node_ids = ent["node_ids"] or ""
            parts = [x.strip() for x in node_ids.split(",") if x.strip()]
            # Reemplazar dup_id por keep_id
            new_parts = []
            for p in parts:
                if p == str(dup_id):
                    if str(keep_id) not in new_parts:
                        new_parts.append(str(keep_id))
                else:
                    new_parts.append(p)
            new_ids = ",".join(new_parts)
            db.execute("UPDATE entities SET node_ids = ?, mention_count = ? WHERE id = ?",
                       (new_ids, len(new_parts), ent["id"]))

        # 4) Eliminar el nodo duplicado
        db.execute("DELETE FROM nodes WHERE id = ?", (dup_id,))

    def dedup(self) -> Dict[str, int]:
        """Encuentra y fusiona nodos duplicados o casi-duplicados."""
        db = self._db()
        merged = 0
        removed = 0

        try:
            rows = db.execute(
                "SELECT id, content, title, category, content_hash, importance "
                "FROM nodes ORDER BY importance DESC"
            ).fetchall()

            # ── Duplicados exactos (mismo content_hash) ──────────────────────
            hash_groups: Dict[str, list] = {}
            for row in rows:
                h = row["content_hash"]
                hash_groups.setdefault(h, []).append(row)

            for h, group in hash_groups.items():
                if len(group) <= 1:
                    continue
                keep = group[0]
                for dup in group[1:]:
                    self._merge_node(db, keep["id"], dup["id"])
                    removed += 1

            # ── Casi-duplicados (Jaccard > threshold, misma categoría) ──────
            # Re-fetch tras cambios
            rows = db.execute(
                "SELECT id, content, category, importance FROM nodes "
                "ORDER BY importance DESC"
            ).fetchall()
            id_set = {r["id"] for r in rows}
            seen = set()
            for i, a in enumerate(rows):
                if a["id"] not in id_set:
                    continue
                for b in rows[i + 1 : min(i + 80, len(rows))]:
                    if b["id"] not in id_set:
                        continue
                    pair = (min(a["id"], b["id"]), max(a["id"], b["id"]))
                    if pair in seen:
                        continue
                    seen.add(pair)
                    if a["category"] != b["category"]:
                        continue
                    sim = self._jaccard(
                        self._word_set(a["content"]),
                        self._word_set(b["content"]),
                    )
                    if sim >= MERGE_HASH_THRESHOLD:
                        keep = a if a["importance"] >= b["importance"] else b
                        dup = b if keep["id"] == a["id"] else a
                        if dup["id"] in id_set:
                            self._merge_node(db, keep["id"], dup["id"])
                            id_set.discard(dup["id"])
                            merged += 1

            db.commit()
        finally:
            db.close()

        logger.info(f"Dedup: {removed} exact dupes removed, {merged} near-dupes merged")
        return {"removed": removed, "merged": merged}

    # ── 2. TTL / Archival ─────────────────────────────────────────────────────

    def archive_old(self) -> int:
        """Archiva nodos viejos de baja importancia (los marca como archived)."""
        db = self._db()
        archived = 0

        try:
            now = datetime.now(timezone.utc)

            # Crear tabla de archive si no existe
            db.execute("""
                CREATE TABLE IF NOT EXISTS archived_nodes (
                    id INTEGER PRIMARY KEY,
                    content TEXT, title TEXT, category TEXT, source TEXT,
                    importance INTEGER, tags TEXT, content_hash TEXT,
                    created_at TEXT, updated_at TEXT,
                    access_count INTEGER, last_accessed TEXT,
                    archived_at TEXT
                )
            """)

            # TTL para nodos de baja importancia (< 4)
            cutoff_low = (now - timedelta(days=TTL_DAYS_LOW_IMPORTANCE)).isoformat()
            rows = db.execute(
                "SELECT * FROM nodes WHERE importance < 4 AND created_at < ?",
                (cutoff_low,)
            ).fetchall()

            for row in rows:
                db.execute(
                    """INSERT INTO archived_nodes
                       (id, content, title, category, source, importance, tags,
                        content_hash, created_at, updated_at, access_count, last_accessed, archived_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["content"], row["title"], row["category"],
                     row["source"], row["importance"], row["tags"], row["content_hash"],
                     row["created_at"], row["updated_at"], row["access_count"],
                     row["last_accessed"], now.isoformat())
                )
                # Remove edges
                db.execute("DELETE FROM edges WHERE from_node = ? OR to_node = ?",
                           (row["id"], row["id"]))
                db.execute("DELETE FROM nodes WHERE id = ?", (row["id"],))
                archived += 1

            # TTL para nodos generales viejos (> 1 año, importance < 6)
            cutoff_general = (now - timedelta(days=TTL_DAYS_GENERAL)).isoformat()
            rows2 = db.execute(
                "SELECT * FROM nodes WHERE importance < 6 AND created_at < ? AND category = 'general'",
                (cutoff_general,)
            ).fetchall()

            for row in rows2:
                db.execute(
                    """INSERT INTO archived_nodes
                       (id, content, title, category, source, importance, tags,
                        content_hash, created_at, updated_at, access_count, last_accessed, archived_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["content"], row["title"], row["category"],
                     row["source"], row["importance"], row["tags"], row["content_hash"],
                     row["created_at"], row["updated_at"], row["access_count"],
                     row["last_accessed"], now.isoformat())
                )
                db.execute("DELETE FROM edges WHERE from_node = ? OR to_node = ?",
                           (row["id"], row["id"]))
                db.execute("DELETE FROM nodes WHERE id = ?", (row["id"],))
                archived += 1

            db.commit()
        finally:
            db.close()

        logger.info(f"Archived: {archived} old nodes")
        return archived

    # ── 3. Compression ────────────────────────────────────────────────────────

    def compress_low_value(self) -> int:
        """Comprime nodos de bajo valor: resume content a 1 línea."""
        db = self._db()
        compressed = 0

        try:
            rows = db.execute(
                """SELECT * FROM nodes
                   WHERE access_count < ? AND importance < 4
                   AND length(content) > 200""",
                (COMPRESS_THRESHOLD,)
            ).fetchall()

            for row in rows:
                # Comprimir: tomar primera línea + importancia
                first_line = row["content"].split("\n")[0][:150]
                compressed_content = f"[compressed] {first_line} (importance={row['importance']}, accessed={row['access_count']}x)"
                db.execute(
                    "UPDATE nodes SET content = ?, updated_at = ? WHERE id = ?",
                    (compressed_content, datetime.now(timezone.utc).isoformat(), row["id"])
                )
                compressed += 1

            db.commit()
        finally:
            db.close()

        logger.info(f"Compressed: {compressed} low-value nodes")
        return compressed

    # ── 4. Pruning (hard limit) ───────────────────────────────────────────────

    def enforce_limits(self) -> Dict[str, int]:
        """Aplica límites duros: si se exceden, prune por importancia."""
        db = self._db()
        pruned = {"nodes": 0, "edges": 0, "entities": 0}

        try:
            # Prune nodes
            node_count = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            if node_count > MAX_NODES:
                excess = node_count - MAX_NODES
                # Borrar los menos importantes y más viejos
                db.execute(
                    """DELETE FROM nodes WHERE id IN (
                        SELECT id FROM nodes ORDER BY importance ASC, access_count ASC, created_at ASC
                        LIMIT ?
                    )""",
                    (excess,)
                )
                pruned["nodes"] = excess

            # Prune edges
            edge_count = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            if edge_count > MAX_EDGES:
                excess = edge_count - MAX_EDGES
                db.execute(
                    """DELETE FROM edges WHERE id IN (
                        SELECT id FROM edges ORDER BY weight ASC, created_at ASC
                        LIMIT ?
                    )""",
                    (excess,)
                )
                pruned["edges"] = excess

            # Prune entities
            entity_count = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            if entity_count > MAX_ENTITIES:
                excess = entity_count - MAX_ENTITIES
                db.execute(
                    """DELETE FROM entities WHERE id IN (
                        SELECT id FROM entities ORDER BY mention_count ASC
                        LIMIT ?
                    )""",
                    (excess,)
                )
                pruned["entities"] = excess

            db.commit()
        finally:
            db.close()

        if any(v > 0 for v in pruned.values()):
            logger.warning(f"Enforced limits: {pruned}")
        return pruned

    # ── 5. Full cleanup ───────────────────────────────────────────────────────

    def cleanup(self) -> Dict:
        """Ejecuta limpieza completa anti-crecimiento."""
        results = {
            "dedup": self.dedup(),
            "archived": self.archive_old(),
            "compressed": self.compress_low_value(),
            "limits": self.enforce_limits(),
        }
        # 6) Limpiar edges huérfanos
        db = self._db()
        orphan = db.execute("""
            SELECT COUNT(*) FROM edges e
            WHERE NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.from_node)
               OR NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.to_node)
        """).fetchone()[0]
        if orphan > 0:
            db.execute("""
                DELETE FROM edges WHERE id IN (
                    SELECT e.id FROM edges e
                    WHERE NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.from_node)
                       OR NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.to_node)
                )
            """)
            db.commit()
            results["orphan_edges"] = orphan

        # VACUUM
        db.execute("VACUUM")
        db.close()

        return results

    # ── 6. Stats ──────────────────────────────────────────────────────────────

    def status(self) -> Dict:
        """Estado del guard y del grafo."""
        db = self._db()
        try:
            nodes = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edges = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            entities = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            archived = 0
            try:
                archived = db.execute("SELECT COUNT(*) FROM archived_nodes").fetchone()[0]
            except:
                pass

            # Low value nodes (candidates for compression/pruning)
            low_value = db.execute(
                "SELECT COUNT(*) FROM nodes WHERE access_count < 3 AND importance < 4"
            ).fetchone()[0]

            # Old nodes (candidates for archival)
            old_threshold = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            old_nodes = db.execute(
                "SELECT COUNT(*) FROM nodes WHERE created_at < ? AND importance < 4",
                (old_threshold,)
            ).fetchone()[0]

            db_size = os.path.getsize(self.db_path) / 1024 if self.db_path.exists() else 0

            return {
                "nodes": nodes,
                "edges": edges,
                "entities": entities,
                "archived": archived,
                "low_value_nodes": low_value,
                "old_nodes": old_nodes,
                "db_size_kb": round(db_size, 1),
                "max_nodes": MAX_NODES,
                "max_edges": MAX_EDGES,
                "max_entities": MAX_ENTITIES,
                "headroom": {
                    "nodes": MAX_NODES - nodes,
                    "edges": MAX_EDGES - edges,
                    "entities": MAX_ENTITIES - entities,
                },
                "ttl_days_low": TTL_DAYS_LOW_IMPORTANCE,
                "ttl_days_general": TTL_DAYS_GENERAL,
            }
        finally:
            db.close()


def get_brain_guard(db_path: Optional[str] = None) -> BrainGuard:
    return BrainGuard(db_path)
