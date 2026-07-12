"""
Gema Sage - Gestor de conocimiento y memoria para SuperNEXUS v2.0

Sage es el agente responsable de gestionar y ordenar la biblioteca y memoria
de conocimientos. Analiza contenido, persiste en cerebro.db, organiza,
deduplica y mantiene la coherencia del conocimiento a largo plazo.

Flujo actual:
  1. analyze_and_persist() → cerebro.guardar_conocimiento()
  2. recell() → cerebro.obtener_conocimientos() con keyword matching
  3. Consolidación periódica de duplicados
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SageGem:
    """Gema especializado en gestion y orden de la biblioteca de conocimiento.
    
    Punto de entrada unico para persistir, recuperar y consolidar conocimiento.
    Escribe a cerebro.db como fuente de verdad unica.
    """
    
    def __init__(self):
        self.cerebro_db = Path.home() / ".nexus" / "brain" / "cerebro.db"
        self._ensure_fts5()

    def _ensure_fts5(self):
        """Crea tabla FTS5 si no existe para busqueda full-text."""
        try:
            conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
            try:
                c = conn.cursor()
                c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS conocimientos_fts 
                             USING fts5(tema, contenido, fuente, content='conocimientos', content_rowid='id')""")
                # Triggers para mantener FTS sincronizado
                c.execute("""CREATE TRIGGER IF NOT EXISTS conocimientos_ai AFTER INSERT ON conocimientos BEGIN
                             INSERT INTO conocimientos_fts(rowid, tema, contenido, fuente) 
                             VALUES (new.id, new.tema, new.contenido, new.fuente); END""")
                c.execute("""CREATE TRIGGER IF NOT EXISTS conocimientos_ad AFTER DELETE ON conocimientos BEGIN
                             INSERT INTO conocimientos_fts(conocimientos_fts, rowid, tema, contenido, fuente) 
                             VALUES('delete', old.id, old.tema, old.contenido, old.fuente); END""")
                c.execute("""CREATE TRIGGER IF NOT EXISTS conocimientos_au AFTER UPDATE ON conocimientos BEGIN
                             INSERT INTO conocimientos_fts(conocimientos_fts, rowid, tema, contenido, fuente) 
                             VALUES('delete', old.id, old.tema, old.contenido, old.fuente);
                             INSERT INTO conocimientos_fts(rowid, tema, contenido, fuente) 
                             VALUES (new.id, new.tema, new.contenido, new.fuente); END""")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
                logger.warning(f"FTS5 setup failed: {e}")

    # ── Persistir conocimiento ─────────────────────────────────────────

    def _infer_topic(self, content: str, source: str = "") -> str:
        """Infers topic from content keywords without LLM."""
        _TOPICS = {
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pip", "pytest", "poetry"],
            "javascript": ["javascript", "typescript", "react", "vue", "angular", "node", "npm", "deno", "nextjs", "svelte"],
            "web": ["html", "css", "http", "rest", "api", "graphql", "websocket", "web", "frontend", "backend"],
            "database": ["sql", "postgres", "mysql", "mongodb", "redis", "sqlite", "orm", "query"],
            "devops": ["docker", "kubernetes", "ci/cd", "github actions", "terraform", "ansible", "nginx"],
            "ai": ["inteligencia artificial", "machine learning", "deep learning", "neural", "gpt", "llm", "modelo", "entrenamiento"],
            "tutorial": ["curso", "tutorial", "guia", "introduccion", "aprender", "desde cero", "basico"],
        }
        text = (content + " " + source).lower()
        scores = {}
        for topic, kws in _TOPICS.items():
            scores[topic] = sum(2 if kw in source.lower() else 1 for kw in kws if kw in text)
        if max(scores.values()) > 1:
            return max(scores, key=scores.get)
        # Check source for github repo language hints
        if "github.com" in source:
            src_lower = source.lower()
            if any(kw in src_lower for kw in ("python", "django", "flask")):
                return "python"
            if any(kw in src_lower for kw in ("js", "ts", "react", "vue", "angular", "node")):
                return "javascript"
        return "general"

    def _extract_essence(self, content: str) -> Dict:
        """Extracts title, summary, key points, code examples from content."""
        import re as _re
        lines = content.split("\n")
        title = ""
        summary = ""
        key_points = []
        code_examples = []

        # Title: first non-empty line that's not a URL or badge
        for line in lines:
            line = line.strip()
            if line and not line.startswith(("[![")) and "http" not in line[:20]:
                title = _re.sub(r'^#+\s*', '', line)[:100]
                break

        # Summary: first meaningful paragraph (non-empty, non-header, non-list)
        for line in lines:
            line = line.strip()
            if len(line) > 40 and not line.startswith(("#", "-", "*", "1.", "![", "http")):
                summary = line[:300]
                break
        if not summary:
            summary = content[:200]

        # Key points: bullet or numbered list items
        for line in lines:
            line = line.strip()
            if line.startswith(("- ", "* ", "1.", "2.", "3.")):
                clean = _re.sub(r'^[\d\*\-\s\.]+', '', line).strip()
                if clean and len(clean) > 10:
                    key_points.append(clean[:150])

        # Code examples: markdown code blocks
        in_code = False
        buf = ""
        for line in lines:
            if line.startswith("```"):
                if in_code:
                    if buf.strip():
                        code_examples.append(buf.strip()[:300])
                    buf = ""
                    in_code = False
                else:
                    in_code = True
            elif in_code:
                buf += line + "\n"

        return {
            "title": title or content[:60],
            "summary": summary,
            "key_points": key_points[:8],
            "code_examples": code_examples[:3],
        }

    async def analyze_and_persist(self, content: str, source: str, category: str = "general", topic: str = None) -> Dict:
        """Analiza contenido y lo persiste en cerebro.db como conocimiento.

        Args:
            content: Texto del contenido a almacenar
            source: Origen (url, manual, conversation, etc.)
            category: Categoria tematica
            topic: Tema exacto (si no se provee, se deriva de source/category)

        Returns:
            Dict con resultado de la operacion
        """
        import re as _re
        content = _re.sub(r'<[^>]+>', '', content)
        content = _re.sub(r'\n{3,}', '\n\n', content).strip()

        # Auto-tagging: infer category from content
        inferred = self._infer_topic(content, source)
        if category == "general" and inferred != "general":
            category = inferred

        # Extract essence for summary field
        essence = self._extract_essence(content)
        enriched = (
            f"# {essence['title']}\n\n"
            f"{essence['summary']}\n\n"
            f"## Temas\n" + "\n".join(f"- {p}" for p in essence['key_points']) + "\n\n"
            "## Codigo\n" + "\n\n".join(f"```\n{e}\n```" for e in essence['code_examples'])
        )
        enriched += f"\n\n---\n\n{content[:8000]}"

        if not topic:
            topic = f"{category}:{essence['title']}" if essence['title'] else source
        logger.info(f"Sage persist: topic={topic[:50]} ({len(enriched)} chars)")

        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Check if topic already exists
        c.execute("SELECT id, contenido, utilidad, veces_revisado FROM conocimientos WHERE tema = ?", (topic,))
        existing = c.fetchone()
        if existing:
            old_content = existing[1] or ""
            new_content = enriched if len(enriched) > len(old_content) else old_content
            new_util = min((existing[2] or 5) + 1, 10)
            c.execute("""UPDATE conocimientos SET contenido=?, fuente=?, fecha=?, utilidad=?, veces_revisado=veces_revisado+1 WHERE id=?""",
                     (new_content, source, now, new_util, existing[0]))
            fact_id = f"fact_{existing[0]}"
            logger.info(f"Sage updated existing conocimiento #{existing[0]}")
        else:
            c.execute("""INSERT INTO conocimientos (tema, contenido, fuente, fecha, utilidad) VALUES (?, ?, ?, ?, ?)""",
                     (topic, enriched, source, now, 6))
            fact_id = f"fact_{c.lastrowid}"
            logger.info(f"Sage created new conocimiento #{c.lastrowid}")

        conn.commit()
        conn.close()
        return {"success": True, "fact_id": fact_id, "category": category}

    # ── Recuperar conocimiento ─────────────────────────────────────────

    async def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca conocimiento relevante en cerebro.db via FTS5.
        
        Args:
            query: Texto de busqueda (soporta sintaxis FTS5: OR, NOT, "frase exacta")
            limit: Maximo de resultados
        
        Returns:
            Lista de dicts con tema, contenido, fuente, fecha, utilidad
        """
        import re
        raw = re.sub(r'[^\w\s]', ' ', query)[:100]
        _STOP = {"que","es","de","en","la","el","los","las","del","con","por","para","un","una",
                 "se","no","lo","su","al","como","mas","pero","sus","le","ya","este","esta",
                 "the","and","for","are","but","not","you","all","can","had","her","was",
                 "one","our","out","has","have","been","some","them","than","what","when",
                 "which","will","with","your"}
        words = [w.lower() for w in raw.split() if len(w) > 2 and w.lower() not in _STOP]
        if not words:
            return []

        # Intentar FTS5 primero
        fts_query = " OR ".join(words)
        matched = []
        try:
            conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
            c = conn.cursor()
            # Rebuild FTS si esta vacio o corrupto
            c.execute("SELECT COUNT(*) FROM conocimientos_fts")
            fts_count = c.fetchone()[0]
            if fts_count == 0:
                c.execute("INSERT INTO conocimientos_fts(conocimientos_fts) VALUES('rebuild')")
                conn.commit()
            
            c.execute("""SELECT k.id, k.tema, k.contenido, k.fuente, k.fecha, k.utilidad, k.veces_revisado,
                                rank
                         FROM conocimientos_fts fts
                         JOIN conocimientos k ON k.id = fts.rowid
                         WHERE conocimientos_fts MATCH ?
                         ORDER BY rank
                         LIMIT ?""", (fts_query, limit * 3))
            rows = c.fetchall()
            conn.close()
            
            now = datetime.now(timezone.utc)
            for r in rows:
                score = abs(r[7]) or 1.0  # rank es negativo (menor = mejor)
                # Recency boost
                if r[4]:
                    try:
                        f = datetime.fromisoformat(r[4])
                        if f.tzinfo is None:
                            f = f.replace(tzinfo=timezone.utc)
                        days_old = (now - f).days
                        if days_old < 7: score += 2
                        elif days_old < 30: score += 1
                    except Exception: pass
                # Revision boost
                score += (r[6] or 0) // 5
                matched.append((score, r))
        except Exception as e:
            logger.warning(f"FTS5 search failed, falling back to keyword: {e}")
            # Fallback: keyword matching legacy
            conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
            c = conn.cursor()
            c.execute("SELECT id, tema, contenido, fuente, fecha, utilidad, veces_revisado FROM conocimientos ORDER BY utilidad DESC")
            rows = c.fetchall()
            conn.close()
            now = datetime.now(timezone.utc)
            for r in rows:
                haystack = " ".join([(r[1] or ""), (r[2] or ""), (r[3] or "")]).lower()
                if not any(w in haystack for w in words): continue
                score = sum(3 if w in (r[1] or "").lower() or w in (r[3] or "").lower() else 1 for w in words)
                if r[4]:
                    try:
                        f = datetime.fromisoformat(r[4])
                        if f.tzinfo is None: f = f.replace(tzinfo=timezone.utc)
                        days_old = (now - f).days
                        if days_old < 7: score += 2
                        elif days_old < 30: score += 1
                    except Exception: pass
                score += (r[6] or 0) // 5
                matched.append((score, r))

        matched.sort(key=lambda x: (x[0], x[1][5]), reverse=True)
        return [
            {"tema": r[1], "contenido": r[2][:500], "fuente": r[3], "fecha": r[4], "utilidad": r[5]}
            for _, r in matched[:limit]
        ]

    # ── Mantenimiento de memoria ────────────────────────────────────────

    def memory_maintenance(self, dry_run: bool = False) -> Dict:
        """Mantenimiento completo de la base de conocimiento.

        Operaciones:
        1. Dedup por contenido similar (MinHash LSH, Jaccard > 0.5): merge
        2. Pruning: eliminar entradas con utilidad < 3 y edad > 90 dias
        3. Pruning: eliminar entradas sin fuente y sin revisiones
        4. Compact: reindexar FTS5 si existe

        Args:
            dry_run: Si True, solo reporta sin modificar

        Returns:
            Dict con estadisticas de las operaciones
        """
        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        now = datetime.now(timezone.utc)
        result = {"dedup_merged": 0, "pruned_low_utility": 0, "pruned_orphan": 0, "errors": []}

        # 1. Dedup por contenido similar via MinHash LSH
        try:
            from datasketch import MinHash, MinHashLSH
            lsh = MinHashLSH(threshold=0.5, num_perm=128)
            c.execute("SELECT id, tema, contenido, fuente, utilidad FROM conocimientos ORDER BY id")
            rows = c.fetchall()
            to_merge = []  # (id_a, id_b, util_a, util_b, cont_a, cont_b, tema_a, tema_b)
            
            for r in rows:
                rid, tema, cont, src, util = r
                if not cont or len(cont) < 50:
                    continue
                # Crear MinHash
                m = MinHash(num_perm=128)
                for word in cont.lower().split():
                    m.update(word.encode('utf8'))
                # Buscar duplicados
                try:
                    candidates = lsh.query(m)
                    for cand_id in candidates:
                        if cand_id == str(rid):
                            continue
                        # Obtener datos del candidato
                        c2 = conn.cursor()
                        c2.execute("SELECT tema, contenido, utilidad FROM conocimientos WHERE id=?", (int(cand_id),))
                        cand = c2.fetchone()
                        if cand:
                            to_merge.append((rid, int(cand_id), util or 5, cand[2] or 5, cont, cand[1], tema, cand[0]))
                except Exception:
                    pass
                # Insertar en LSH
                lsh.insert(str(rid), m)
            
            if not dry_run:
                seen = set()
                for id_a, id_b, util_a, util_b, cont_a, cont_b, tema_a, tema_b in to_merge:
                    if id_b in seen:
                        continue
                    seen.add(id_b)
                    new_util = min(util_a + util_b, 10)
                    new_cont = cont_a if len(cont_a) >= len(cont_b) else cont_b
                    new_tema = tema_a if len(tema_a) <= len(tema_b) else tema_b
                    c.execute("UPDATE conocimientos SET contenido=?, utilidad=?, veces_revisado=veces_revisado+1 WHERE id=?",
                              (new_cont, new_util, id_a))
                    c.execute("DELETE FROM conocimientos WHERE id=?", (id_b,))
            result["dedup_merged"] = len(set(b for _, b, *_ in to_merge))
        except ImportError:
            logger.warning("datasketch not installed, skipping MinHash dedup")
        except Exception as e:
            result["errors"].append(f"minhash_dedup: {e}")

        # 2. Pruning: baja utilidad y antigua
        cutoff_90 = now.isoformat()
        try:
            c.execute("""SELECT id, utilidad, fecha FROM conocimientos""")
            for row in c.fetchall():
                rid, util, fecha_str = row
                util = util or 5
                if util >= 3:
                    continue
                if not fecha_str:
                    continue
                try:
                    fecha = datetime.fromisoformat(fecha_str)
                    if fecha.tzinfo is None:
                        fecha = fecha.replace(tzinfo=timezone.utc)
                    if (now - fecha).days > 90:
                        if not dry_run:
                            c.execute("DELETE FROM conocimientos WHERE id=?", (rid,))
                        result["pruned_low_utility"] += 1
                except Exception:
                    pass
        except Exception as e:
            result["errors"].append(f"prune_low_utility: {e}")

        # 3. Pruning: entradas huerfanas (sin fuente, sin revisiones)
        try:
            c.execute("""SELECT id, fuente, veces_revisado FROM conocimientos WHERE (fuente IS NULL OR fuente = '')""")
            for row in c.fetchall():
                rid, src, rev = row
                rev = rev or 0
                if rev == 0:
                    if not dry_run:
                        c.execute("DELETE FROM conocimientos WHERE id=?", (rid,))
                    result["pruned_orphan"] += 1
        except Exception as e:
            result["errors"].append(f"prune_orphan: {e}")

        if not dry_run:
            conn.commit()
        conn.close()
        total = result["dedup_merged"] + result["pruned_low_utility"] + result["pruned_orphan"]
        if total:
            logger.info(f"Sage memory_maintenance: {result}")
        return result

    def archive_old(self, dry_run: bool = False) -> Dict:
        """Archiva conocimiento viejo: reemplaza contenido crudo por resumen.

        Estrategia:
        - Hot (< 30 dias): sin cambios
        - Warm (30-90 dias): conserva solo essence (sin raw)
        - Cold (> 90 dias y utilidad < 5): solo titulo + resumen

        Args:
            dry_run: Si True, solo reporta sin modificar

        Returns:
            Dict con estadisticas
        """
        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        now = datetime.now(timezone.utc)
        result = {"warm_compressed": 0, "cold_compressed": 0, "errors": []}

        c.execute("SELECT id, tema, contenido, fecha, utilidad FROM conocimientos")
        rows = c.fetchall()
        for row in rows:
            rid, tema, contenido, fecha_str, utilidad = row
            if not fecha_str or not contenido:
                continue
            try:
                fecha = datetime.fromisoformat(fecha_str)
                if fecha.tzinfo is None:
                    fecha = fecha.replace(tzinfo=timezone.utc)
                days_old = (now - fecha).days
            except Exception:
                continue
            utilidad = utilidad or 5

            # Warm: 30-90 dias, keep only essence
            if 30 <= days_old < 90 and len(contenido) > 1000:
                essence = self._extract_essence(contenido)
                compressed = (
                    f"# {essence['title']}\n\n{essence['summary']}\n\n"
                    f"## Temas\n" + "\n".join(f"- {p}" for p in essence['key_points']) + "\n\n"
                    "## Codigo\n" + "\n\n".join(f"```\n{e}\n```" for e in essence['code_examples'])
                )
                if len(compressed) < len(contenido) * 0.7:
                    if not dry_run:
                        c.execute("UPDATE conocimientos SET contenido=? WHERE id=?", (compressed, rid))
                    result["warm_compressed"] += 1

            # Cold: > 90 days and low utility, only title + summary
            elif days_old >= 90 and utilidad < 5 and len(contenido) > 300:
                essence = self._extract_essence(contenido)
                compressed = f"# {essence['title']}\n\n{essence['summary']}"
                if not dry_run:
                    c.execute("UPDATE conocimientos SET contenido=? WHERE id=?", (compressed, rid))
                result["cold_compressed"] += 1

        if not dry_run:
            conn.commit()
        conn.close()
        total = result["warm_compressed"] + result["cold_compressed"]
        if total:
            logger.info(f"Sage archive_old: {result}")
        return result

    def run_full_maintenance(self, dry_run: bool = False) -> Dict:
        """Ejecuta todo el pipeline de mantenimiento."""
        result = {"memory_maintenance": self.memory_maintenance(dry_run=dry_run)}
        result["archive_old"] = self.archive_old(dry_run=dry_run)
        result["consolidate"] = self.consolidate() if not dry_run else {"merged": 0, "domains": 0}
        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM conocimientos")
        result["total_after"] = c.fetchone()[0]
        conn.close()
        return result

    # ── Consolidar y ordenar (legacy) ───────────────────────────────────

    def consolidate(self) -> Dict:
        """Consolida entradas duplicadas (mismo source URL) en cerebro.db.

        Fusiona entradas con la misma fuente URL normalizada:
        - Suma utilidad y revisiones
        - Conserva el contenido mas largo
        - Conserva la fecha mas antigua

        Returns:
            Dict con estadisticas de la consolidacion
        """
        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        c.execute("SELECT id, tema, contenido, fuente, utilidad, veces_revisado, fecha, consolidado FROM conocimientos ORDER BY fuente")
        rows = c.fetchall()

        from urllib.parse import urlparse
        groups = {}
        for r in rows:
            src = (r[3] or "").strip().lower()
            if not src.startswith(("http://", "https://", "url:")):
                continue
            src = src.removeprefix("url:").rstrip("/")
            # Group by full path, not just domain, to avoid merging different repos on same host
            key = urlparse(src).path.rstrip("/")
            if key:
                groups.setdefault(key, []).append(r)

        merged = 0
        for domain, entries in groups.items():
            if len(entries) < 2:
                continue
            best = max(entries, key=lambda x: (x[4] or 5) + (x[5] or 0))
            for other in entries:
                if other[0] == best[0]:
                    continue
                new_util = min((best[4] or 5) + (other[4] or 5), 10)
                new_rev = (best[5] or 0) + (other[5] or 0)
                b_content = best[2] or ""
                o_content = other[2] or ""
                new_content = b_content if len(b_content) >= len(o_content) else o_content
                b_tema = best[1] or ""
                o_tema = other[1] or ""
                new_tema = min(b_tema, o_tema, key=len)  # prefer shorter tema
                dates = [d for d in (best[6], other[6]) if d]
                new_fecha = min(dates) if dates else best[6]
                new_cons = best[7] or other[7]
                c.execute("""UPDATE conocimientos SET tema=?, contenido=?, utilidad=?, veces_revisado=?, fecha=?, consolidado=? WHERE id=?""",
                         (new_tema, new_content, new_util, new_rev, new_fecha, new_cons, best[0]))
                c.execute("DELETE FROM conocimientos WHERE id=?", (other[0],))
                merged += 1

        conn.commit()
        conn.close()

        if merged:
            logger.info(f"Sage consolidation: {merged} duplicates merged for {len(groups)} domains")
        return {"merged": merged, "domains": len(groups)}

    # ── Estadisticas ───────────────────────────────────────────────────

    def get_memory_stats(self) -> Dict:
        """Estadisticas de la base de conocimiento"""
        conn = sqlite3.connect(str(self.cerebro_db), timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM conocimientos")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT fuente) FROM conocimientos")
        sources = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM conocimientos WHERE fuente LIKE 'http%' OR fuente LIKE 'url:%'")
        urls = c.fetchone()[0]
        conn.close()
        return {
            "total_conocimientos": total,
            "fuentes_distintas": sources,
            "urls_almacenadas": urls,
            "gestor": "sage_gem",
        }
