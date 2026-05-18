"""
Cerebro Adaptativo para SuperNEXUS v2
Aprende del usuario, personaliza respuestas, mantiene memoria de preferencias.

Mejoras implementadas (basadas en Agent_Memory_Techniques de NirDiamant):
- Memoria episódica: Eventos específicos con contexto temporal
- Memoria semántica: Conocimientos generales consolidados
- Consolidación automática: Mover recuerdos frecuentes a largo plazo
- Olvido selectivo: Eliminar recuerdos poco usados para mantener eficiencia
- Memoria de trabajo: Contexto reciente de conversaciones
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Cerebro:
    """
    Cerebro generico que aprende del usuario.
    
    Arquitectura de memoria (basada en patrones de NirDiamant):
    - Memoria de trabajo: Últimas conversaciones (corto plazo)
    - Memoria episódica: Eventos específicos con contexto
    - Memoria semántica: Conocimientos consolidados (largo plazo)
    - Memoria procedimental: Patrones de comportamiento aprendidos
    """

    def __init__(self, user_data_dir: str = None):
        self.user_dir = Path(user_data_dir or os.path.expanduser("~/.nexus/brain"))
        self.user_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.user_dir / "cerebro.db"
        self._init_db()

        self.config = self._load_config()
        self.learning = {
            "conversations": 0,
            "commands_executed": 0,
            "tools_used": set(),
            "preferred_gem": "general",
            "preferred_model": "auto",
            "topics_interests": {},
            "complexity_level": 1,
            "last_consolidation": None,
        }
        self._load_learning_state()
        
        # Memoria de trabajo (últimas interacciones en memoria)
        self.working_memory: List[Dict] = []
        self.working_memory_limit = 10
        
        logger.info(f"Cerebro initialized at {self.user_dir}")

    def _get_conn(self) -> sqlite3.Connection:
        """Obtiene conexion con WAL mode y busy_timeout para concurrencia"""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        # Memoria general (preferencias, configuraciones)
        c.execute("""CREATE TABLE IF NOT EXISTS memoria (
            id INTEGER PRIMARY KEY, timestamp TEXT, tipo TEXT,
            clave TEXT, valor TEXT, contexto TEXT,
            importancia INTEGER, veces_usado INTEGER DEFAULT 1)""")
        
        # Patrones de comportamiento (memoria procedimental)
        c.execute("""CREATE TABLE IF NOT EXISTS patrones (
            id INTEGER PRIMARY KEY, patron TEXT, frecuencia INTEGER,
            ultima_vez TEXT, respuesta_preferida TEXT, contexto TEXT)""")
        
        # Conocimientos generales (memoria semántica)
        c.execute("""CREATE TABLE IF NOT EXISTS conocimientos (
            id INTEGER PRIMARY KEY, tema TEXT, contenido TEXT,
            fuente TEXT, fecha TEXT, veces_revisado INTEGER DEFAULT 0,
            utilidad INTEGER DEFAULT 5, consolidado BOOLEAN DEFAULT 0)""")
        
        # Conversaciones (memoria episódica)
        c.execute("""CREATE TABLE IF NOT EXISTS conversaciones (
            id INTEGER PRIMARY KEY, fecha TEXT, gem TEXT,
            mensaje TEXT, respuesta TEXT, aprendio BOOLEAN DEFAULT 0,
            contexto TEXT, emociones TEXT)""")
        
        # Eventos específicos (memoria episódica detallada)
        c.execute("""CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT,
            descripcion TEXT, contexto TEXT, importancia INTEGER,
            relacionado_con TEXT, consolidado BOOLEAN DEFAULT 0)""")
        
        # Relaciones entre conocimientos (grafo semántico básico)
        c.execute("""CREATE TABLE IF NOT EXISTS relaciones (
            id INTEGER PRIMARY KEY, origen TEXT, destino TEXT,
            tipo TEXT, fuerza REAL DEFAULT 1.0, fecha TEXT)""")
        
        conn.commit()
        conn.close()

    def _load_config(self) -> dict:
        config_path = self.user_dir / "config.json"
        default = {
            "nombre_usuario": "", "idioma": "es", "estilo": "directo",
            "tema": "oscuro", "auto_aprender": True, "nivel_proactividad": 5,
            "preferencias_notificaciones": True, "modelo_default": "auto",
            "consolidacion_automatica": True, "olvido_selectivo": True,
        }
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                return {**default, **config}
            except Exception:
                pass
        return default

    def _load_learning_state(self):
        state_path = self.user_dir / "learning.json"
        if state_path.exists():
            try:
                saved = json.loads(state_path.read_text(encoding="utf-8"))
                self.learning.update(saved)
                if "tools_used" in saved and isinstance(saved["tools_used"], list):
                    self.learning["tools_used"] = set(saved["tools_used"])
            except Exception:
                pass

    def _save_learning_state(self):
        state_path = self.user_dir / "learning.json"
        state = self.learning.copy()
        state["tools_used"] = list(state["tools_used"])
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    async def aprender_interaccion(self, prompt: str, respuesta: str, gem: str, contexto: str = ""):
        """
        Aprende de cada interaccion (memoria episódica).
        
        Basado en patrones de Agent_Memory_Techniques:
        - Guarda evento con contexto temporal
        - Actualiza memoria de trabajo
        - Detecta temas de interés
        - Programa consolidación si es necesario
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        # Guardar conversación
        c.execute("INSERT INTO conversaciones (fecha, gem, mensaje, respuesta, contexto) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), gem, prompt, respuesta, contexto))
        self.learning["conversations"] += 1

        # Detectar temas
        temas = self._detectar_temas(prompt)
        for tema in temas:
            self.learning["topics_interests"][tema] = \
                self.learning["topics_interests"].get(tema, 0) + 1

        # Actualizar preferencia de gem
        c.execute("SELECT COUNT(*) FROM conversaciones WHERE gem = ?", (gem,))
        count = c.fetchone()[0]
        c.execute("INSERT OR REPLACE INTO memoria (timestamp, tipo, clave, valor, importancia) VALUES (?, 'preferencia', ?, ?, ?)",
                  (datetime.now().isoformat(), f"gem_{gem}", str(count), 5))
        
        # Guardar como evento episódico
        c.execute("""INSERT INTO eventos (fecha, tipo, descripcion, contexto, importancia) 
                     VALUES (?, 'interaccion', ?, ?, ?)""",
                  (datetime.now().isoformat(), prompt[:200], contexto, 3))
        
        conn.commit()
        conn.close()
        
        # Actualizar memoria de trabajo
        self.working_memory.append({
            "prompt": prompt,
            "respuesta": respuesta,
            "gem": gem,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.working_memory) > self.working_memory_limit:
            self.working_memory.pop(0)
        
        self._save_learning_state()
        
        # Consolidar si hay suficientes interacciones
        if self.config.get("consolidacion_automatica", True):
            await self._check_consolidation()

    async def aprender_patron(self, tipo: str, contexto: str, respuesta: str):
        """Aprende patrones de comportamiento (memoria procedimental)"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT frecuencia, respuesta_preferida FROM patrones WHERE patron = ?", (tipo,))
        row = c.fetchone()
        if row:
            nueva_frecuencia = row[0] + 1
            respuesta_preferida = respuesta if respuesta != row[1] and nueva_frecuencia > 3 else row[1]
            c.execute("UPDATE patrones SET frecuencia = ?, ultima_vez = ?, respuesta_preferida = ? WHERE patron = ?",
                      (nueva_frecuencia, datetime.now().isoformat(), respuesta_preferida, tipo))
        else:
            c.execute("INSERT INTO patrones (patron, frecuencia, ultima_vez, respuesta_preferida, contexto) VALUES (?, 1, ?, ?, ?)",
                      (tipo, datetime.now().isoformat(), respuesta, contexto))
        self.learning["commands_executed"] += 1
        conn.commit()
        conn.close()
        self._save_learning_state()

    async def aprender_herramienta(self, tool_name: str):
        self.learning["tools_used"].add(tool_name)
        self._save_learning_state()

    async def guardar_conocimiento(self, tema: str, contenido: str, fuente: str = "usuario", utilidad: int = 5):
        """
        Guarda conocimiento en memoria semántica.
        
        Basado en patrones de Agent_Memory_Techniques:
        - Conocimientos se consolidan con el tiempo
        - Utilidad determina prioridad de retención
        """
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id FROM conocimientos WHERE tema = ?", (tema,))
        if c.fetchone():
            c.execute("UPDATE conocimientos SET contenido = ?, fuente = ?, fecha = ?, veces_revisado = veces_revisado + 1 WHERE tema = ?",
                      (contenido, fuente, datetime.now().isoformat(), tema))
        else:
            c.execute("INSERT INTO conocimientos (tema, contenido, fuente, fecha, utilidad) VALUES (?, ?, ?, ?, ?)",
                      (tema, contenido, fuente, datetime.now().isoformat(), utilidad))
        conn.commit()
        conn.close()

    def _detectar_temas(self, texto: str) -> list:
        temas_palabras = {
            "codigo": ["codigo", "programa", "funcion", "debug", "python", "javascript"],
            "docker": ["docker", "contenedor", "imagen", "k8s", "kubernetes"],
            "hardware": ["gpu", "cpu", "amd", "nvidia", "ram", "hardware"],
            "red": ["red", "ssh", "ip", "dns", "firewall", "proxy"],
            "ai": ["ia", "modelo", "ollama", "llm", "prompt", "gemma"],
            "linux": ["linux", "ubuntu", "terminal", "bash", "shell"],
            "investigacion": ["buscar", "investigar", "google", "scholar", "estudiar"],
            "sistema": ["sistema", "configurar", "instalar", "setup", "administracion"],
        }
        texto_lower = texto.lower()
        return [tema for tema, palabras in temas_palabras.items()
                if any(p in texto_lower for p in palabras)]

    def obtener_patrones(self, tipo: str = None) -> list:
        conn = self._get_conn()
        c = conn.cursor()
        if tipo:
            c.execute("SELECT * FROM patrones WHERE patron = ?", (tipo,))
        else:
            c.execute("SELECT * FROM patrones ORDER BY frecuencia DESC")
        resultados = c.fetchall()
        conn.close()
        return [{"patron": r[1], "frecuencia": r[2], "respuesta": r[4]} for r in resultados]

    def obtener_conocimientos(self, tema: str = None) -> list:
        conn = self._get_conn()
        c = conn.cursor()
        if tema:
            c.execute("SELECT * FROM conocimientos WHERE tema LIKE ?", (f"%{tema}%",))
        else:
            c.execute("SELECT * FROM conocimientos ORDER BY utilidad DESC")
        resultados = c.fetchall()
        conn.close()
        return [{"tema": r[1], "contenido": r[2], "utilidad": r[6]} for r in resultados]

    def obtener_preferencias(self) -> dict:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT clave, valor, importancia FROM memoria WHERE tipo = 'preferencia'")
        prefs = {row[0]: {"valor": row[1], "importancia": row[2]} for row in c.fetchall()}
        prefs["learning"] = {
            "conversations": self.learning["conversations"],
            "commands_executed": self.learning["commands_executed"],
            "tools_used": list(self.learning["tools_used"]),
            "top_topics": sorted(self.learning["topics_interests"].items(), key=lambda x: x[1], reverse=True)[:5],
            "preferred_gem": self.learning["preferred_gem"],
            "complexity_level": self.learning["complexity_level"],
        }
        conn.close()
        return prefs

    def obtener_estadisticas(self) -> dict:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM conversaciones")
        conv_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM conocimientos")
        know_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM patrones")
        pattern_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM memoria")
        mem_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM eventos")
        event_count = c.fetchone()[0]
        conn.close()
        return {
            "conversaciones": conv_count, "conocimientos": know_count,
            "patrones": pattern_count, "memorias": mem_count,
            "eventos": event_count,
            "interacciones": self.learning["conversations"],
            "herramientas_usadas": len(self.learning["tools_used"]),
            "temas_de_interes": len(self.learning["topics_interests"]),
            "working_memory_size": len(self.working_memory),
        }

    def get_system_prompt_adaptado(self) -> str:
        prefs = self.obtener_preferencias()
        stats = self.obtener_estadisticas()
        estilo = self.config.get("estilo", "directo")
        prompt_parts = [
            "Eres SuperNEXUS, un asistente de IA adaptativo.",
            f"Has tenido {stats['interacciones']} interacciones con este usuario.",
        ]
        if "learning" in prefs and prefs["learning"]["top_topics"]:
            top = [t[0] for t in prefs["learning"]["top_topics"][:3]]
            prompt_parts.append(f"Temas de interes: {', '.join(top)}.")
        estilos = {"directo": "Responde de forma concisa y directa.",
                   "detallado": "Proporciona respuestas detalladas y explicativas.",
                   "creativo": "Usa un estilo creativo y variado."}
        prompt_parts.append(estilos.get(estilo, estilos["directo"]))
        return " ".join(prompt_parts)

    async def set_config(self, key: str, value):
        self.config[key] = value
        config_path = self.user_dir / "config.json"
        config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

    def exportar(self, path: str = None) -> dict:
        if not path:
            path = str(self.user_dir / f"cerebro_export_{datetime.now().strftime('%Y%m%d')}.json")
        conn = self._get_conn()
        export_data = {
            "version": "2.0", "fecha_export": datetime.now().isoformat(),
            "config": self.config, "learning": {**self.learning, "tools_used": list(self.learning["tools_used"])},
            "conversaciones": conn.execute("SELECT * FROM conversaciones").fetchall(),
            "conocimientos": conn.execute("SELECT * FROM conocimientos").fetchall(),
            "patrones": conn.execute("SELECT * FROM patrones").fetchall(),
            "memoria": conn.execute("SELECT * FROM memoria").fetchall(),
            "eventos": conn.execute("SELECT * FROM eventos").fetchall(),
            "relaciones": conn.execute("SELECT * FROM relaciones").fetchall(),
        }
        conn.close()
        with open(path, 'w', encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)
        return {"success": True, "path": path}

    def importar(self, path: str) -> dict:
        with open(path, 'r', encoding="utf-8") as f:
            data = json.load(f)
        conn = self._get_conn()
        c = conn.cursor()
        for table in ("conversaciones", "conocimientos", "patrones", "memoria", "eventos", "relaciones"):
            c.execute(f"DELETE FROM {table}")
        if "conversaciones" in data:
            c.executemany("INSERT INTO conversaciones (id, fecha, gem, mensaje, respuesta, aprendio, contexto, emociones) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data["conversaciones"])
        if "conocimientos" in data:
            c.executemany("INSERT INTO conocimientos (id, tema, contenido, fuente, fecha, veces_revisado, utilidad, consolidado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data["conocimientos"])
        if "patrones" in data:
            c.executemany("INSERT INTO patrones (id, patron, frecuencia, ultima_vez, respuesta_preferida, contexto) VALUES (?, ?, ?, ?, ?, ?)", data["patrones"])
        if "memoria" in data:
            c.executemany("INSERT INTO memoria (id, timestamp, tipo, clave, valor, contexto, importancia, veces_usado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data["memoria"])
        if "eventos" in data:
            c.executemany("INSERT INTO eventos (id, fecha, tipo, descripcion, contexto, importancia, relacionado_con, consolidado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data["eventos"])
        if "relaciones" in data:
            c.executemany("INSERT INTO relaciones (id, origen, destino, tipo, fuerza, fecha) VALUES (?, ?, ?, ?, ?, ?)", data["relaciones"])
        if "config" in data:
            self.config = data["config"]
        if "learning" in data:
            self.learning.update(data["learning"])
            self._save_learning_state()
        conn.commit()
        conn.close()
        return {"success": True, "mensaje": f"Cerebro importado desde {path}"}

    def reset(self) -> dict:
        conn = self._get_conn()
        c = conn.cursor()
        for table in ("conversaciones", "conocimientos", "patrones", "memoria", "eventos", "relaciones"):
            c.execute(f"DELETE FROM {table}")
        self.learning = {"conversations": 0, "commands_executed": 0, "tools_used": set(),
                         "preferred_gem": "general", "preferred_model": "auto",
                         "topics_interests": {}, "complexity_level": 1, "last_consolidation": None}
        self.working_memory = []
        conn.commit()
        conn.close()
        self._save_learning_state()
        return {"success": True, "mensaje": "Cerebro reseteado (config preservada)"}

    async def _check_consolidation(self):
        """Verifica si es necesario consolidar memorias"""
        if self.learning["conversations"] % 20 == 0 and self.learning["conversations"] > 0:
            await self.consolidar_memorias()

    async def consolidar_memorias(self):
        """
        Consolida memorias: Mueve conocimientos frecuentes a largo plazo.
        Basado en patrones de Agent_Memory_Techniques.
        """
        logger.info("Consolidando memorias...")
        conn = self._get_conn()
        c = conn.cursor()
        
        # Consolidar conocimientos con alta utilidad y revisiones
        c.execute("""UPDATE conocimientos SET consolidado = 1 
                     WHERE veces_revisado >= 3 AND utilidad >= 7 AND consolidado = 0""")
        consolidados = c.rowcount
        
        # Consolidar eventos frecuentes
        c.execute("""UPDATE eventos SET consolidado = 1 
                     WHERE importancia >= 7 AND consolidado = 0""")
        eventos_consolidados = c.rowcount
        
        conn.commit()
        conn.close()
        
        self.learning["last_consolidation"] = datetime.now().isoformat()
        self._save_learning_state()
        
        logger.info(f"Consolidacion completada: {consolidados} conocimientos, {eventos_consolidados} eventos")

    async def olvido_selectivo(self, dias_umbral: int = 90):
        """
        Elimina recuerdos poco usados para mantener eficiencia.
        Basado en patrones de Agent_Memory_Techniques.
        """
        if not self.config.get("olvido_selectivo", True):
            return {"success": False, "mensaje": "Olvido selectivo deshabilitado"}
        
        logger.info(f"Ejecutando olvido selectivo (umbral: {dias_umbral} dias)...")
        conn = self._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=dias_umbral)).isoformat()
        
        # Eliminar conversaciones antiguas no aprendidas
        c.execute("DELETE FROM conversaciones WHERE fecha < ? AND aprendio = 0", (cutoff,))
        conv_eliminadas = c.rowcount
        
        # Eliminar eventos antiguos no consolidados
        c.execute("DELETE FROM eventos WHERE fecha < ? AND consolidado = 0", (cutoff,))
        eventos_eliminados = c.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Olvido selectivo: {conv_eliminadas} conversaciones, {eventos_eliminados} eventos eliminados")
        return {"success": True, "conversaciones_eliminadas": conv_eliminadas, "eventos_eliminados": eventos_eliminados}

    def obtener_memoria_trabajo(self) -> List[Dict]:
        """Obtiene memoria de trabajo (contexto reciente)"""
        return self.working_memory.copy()

    def obtener_conocimientos_consolidados(self) -> list:
        """Obtiene conocimientos de largo plazo (consolidados)"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM conocimientos WHERE consolidado = 1 ORDER BY utilidad DESC")
        resultados = c.fetchall()
        conn.close()
        return [{"tema": r[1], "contenido": r[2], "utilidad": r[6]} for r in resultados]

    def obtener_eventos_recientes(self, dias: int = 7) -> list:
        """Obtiene eventos recientes (memoria episódica)"""
        conn = self._get_conn()
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=dias)).isoformat()
        c.execute("SELECT * FROM eventos WHERE fecha > ? ORDER BY fecha DESC", (cutoff,))
        resultados = c.fetchall()
        conn.close()
        return [{"tipo": r[2], "descripcion": r[3], "importancia": r[5]} for r in resultados]
