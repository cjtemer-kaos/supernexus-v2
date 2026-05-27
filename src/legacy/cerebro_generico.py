#!/usr/bin/env python3
"""
NEXUS CEREBRO GENERICO - Sistema de Aprendizaje Adaptativo
El cerebro aprende del usuario y se personaliza progresivamente.
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

class Cerebro:
    """
    Cerebro genérico que aprende del usuario.
    Sin datos previos - comienza vacío y crece con el uso.
    """
    
    def __init__(self, user_data_dir: str = None):
        # Directorio del usuario (datos propios, no incluidos en distribución)
        self.user_dir = user_data_dir or os.path.expanduser("~/.nexus/brain")
        os.makedirs(self.user_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.user_dir, "cerebro.db")
        self.init_db()
        
        # Configuración del usuario
        self.config = self._load_config()
        
        # Estado del aprendizaje
        self.learning = {
            "conversations": 0,
            "commands_executed": 0,
            "tools_used": set(),
            "preferred_gem": "general",
            "preferred_model": "auto",
            "topics_interests": {},  # {topic: count}
            "complexity_level": 1,   # 1-5, aprende del usuario
        }
        
        # Cargar estado de aprendizaje
        self._load_learning_state()
    
    def init_db(self):
        """Inicializar base de datos del cerebro"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Tabla de memoria a largo plazo
        c.execute("""
            CREATE TABLE IF NOT EXISTS memoria (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                tipo TEXT,           -- 'preferencia', 'patron', 'conocimiento', 'historico'
                clave TEXT,
                valor TEXT,
                contexto TEXT,        -- situacion donde aprendio
                importancia INTEGER,  -- 1-10
                veces_usado INTEGER DEFAULT 1
            )
        """)
        
        # Tabla de patrones de usuario
        c.execute("""
            CREATE TABLE IF NOT EXISTS patrones (
                id INTEGER PRIMARY KEY,
                patron TEXT,          -- tipo de patron (comando, pregunta, etc)
                frecuencia INTEGER,
                ultima_vez TEXT,
                respuesta_preferida TEXT,
                contexto TEXT
            )
        """)
        
        # Tabla de conocimientos aprendidos
        c.execute("""
            CREATE TABLE IF NOT EXISTS conocimientos (
                id INTEGER PRIMARY KEY,
                tema TEXT,
                contenido TEXT,
                fuente TEXT,
                fecha TEXT,
                veces_revisado INTEGER DEFAULT 0,
                utilidad INTEGER DEFAULT 5  -- 1-10
            )
        """)
        
        # Tabla de conversaciones importantes
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY,
                fecha TEXT,
               gem TEXT,
                mensaje TEXT,
                respuesta TEXT,
                aprendio BOOLEAN DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_config(self) -> dict:
        """Cargar configuración del usuario"""
        config_path = os.path.join(self.user_dir, "config.json")
        default = {
            "nombre_usuario": "",
            "idioma": "es",
            "estilo": "directo",  # directo, detallado, creativo
            "tema": "oscuro",
            "auto_aprender": True,
            "nivel_proactividad": 5,  # 1-10
            "preferencias_notificaciones": True,
            "modelo_default": "auto",
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                return {**default, **config}
        return default
    
    def _load_learning_state(self):
        """Cargar estado de aprendizaje"""
        state_path = os.path.join(self.user_dir, "learning.json")
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                saved = json.load(f)
                self.learning.update(saved)
                if "tools_used" in saved and isinstance(saved["tools_used"], list):
                    self.learning["tools_used"] = set(saved["tools_used"])
    
    def _save_learning_state(self):
        """Guardar estado de aprendizaje"""
        state_path = os.path.join(self.user_dir, "learning.json")
        state = self.learning.copy()
        state["tools_used"] = list(state["tools_used"])
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    # ==================== APRENDIZAJE ====================
    
    def aprender_interaccion(self, prompt: str, respuesta: str, gem: str):
        """Aprende de cada interacción"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Guardar conversación
        c.execute("""
            INSERT INTO conversaciones (fecha, gem, mensaje, respuesta)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), gem, prompt, respuesta))
        
        # Actualizar contadores
        self.learning["conversations"] += 1
        
        # Detectar temas de interés
        temas = self._detectar_temas(prompt)
        for tema in temas:
            self.learning["topics_interests"][tema] = \
                self.learning["topics_interests"].get(tema, 0) + 1
        
        # Actualizar gem preferido
        c.execute("SELECT COUNT(*) FROM conversaciones WHERE gem = ?", (gem,))
        count = c.fetchone()[0]
        
        # Guardar preferencia
        c.execute("""
            INSERT OR REPLACE INTO memoria (timestamp, tipo, clave, valor, importancia)
            VALUES (?, 'preferencia', ?, ?, ?)
        """, (datetime.now().isoformat(), f"gem_{gem}", str(count), 5))
        
        conn.commit()
        conn.close()
        self._save_learning_state()
    
    def aprender_patron(self, tipo: str, contexto: str, respuesta: str):
        """Aprende patrones de comportamiento"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Ver si existe el patrón
        c.execute("SELECT frecuencia, respuesta_preferida FROM patrones WHERE patron = ?", (tipo,))
        row = c.fetchone()
        
        if row:
            nueva_frecuencia = row[0] + 1
            # Si la nueva respuesta es diferente, actualizar preferida
            if respuesta != row[1] and nueva_frecuencia > 3:
                respuesta_preferida = respuesta
            else:
                respuesta_preferida = row[1]
            
            c.execute("""
                UPDATE patrones 
                SET frecuencia = ?, ultima_vez = ?, respuesta_preferida = ?
                WHERE patron = ?
            """, (nueva_frecuencia, datetime.now().isoformat(), respuesta_preferida, tipo))
        else:
            c.execute("""
                INSERT INTO patrones (patron, frecuencia, ultima_vez, respuesta_preferida, contexto)
                VALUES (?, 1, ?, ?, ?)
            """, (tipo, datetime.now().isoformat(), respuesta, contexto))
        
        self.learning["commands_executed"] += 1
        conn.commit()
        conn.close()
        self._save_learning_state()
    
    def aprender_herramienta(self, tool_name: str):
        """Registra uso de herramientas"""
        self.learning["tools_used"].add(tool_name)
        self._save_learning_state()
    
    def guardar_conocimiento(self, tema: str, contenido: str, fuente: str = "usuario"):
        """Guarda un conocimiento nuevo"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Ver si ya existe
        c.execute("SELECT id FROM conocimientos WHERE tema = ?", (tema,))
        if c.fetchone():
            c.execute("""
                UPDATE conocimientos 
                SET contenido = ?, fuente = ?, fecha = ?, veces_revisado = veces_revisado + 1
                WHERE tema = ?
            """, (contenido, fuente, datetime.now().isoformat(), tema))
        else:
            c.execute("""
                INSERT INTO conocimientos (tema, contenido, fuente, fecha)
                VALUES (?, ?, ?, ?)
            """, (tema, contenido, fuente, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _detectar_temas(self, texto: str) -> list:
        """Detecta temas en el texto"""
        # Palabras clave por categoría
        temas_palabras = {
            "codigo": ["código", "programa", "función", "debug", "python", "javascript"],
            "docker": ["docker", "contenedor", "imagen", "k8s", "kubernetes"],
            "hardware": ["gpu", "cpu", "amd", "nvidia", "ram", "hardware"],
            "red": ["red", "ssh", "ip", "dns", "firewall", "proxy"],
            "ai": ["ia", "modelo", "ollama", "llm", "prompt", "gemma"],
            "linux": ["linux", "ubuntu", "terminal", "bash", "shell", "popos"],
            "investigacion": ["buscar", "investigar", "google", "scholar", "estudiar"],
            "sistema": ["sistema", "configurar", "instalar", "setup", "administración"],
        }
        
        texto_lower = texto.lower()
        temas = []
        
        for tema, palabras in temas_palabras.items():
            if any(p in texto_lower for p in palabras):
                temas.append(tema)
        
        return temas
    
    # ==================== RECUPERACIÓN ====================
    
    def obtener_patrons(self, tipo: str = None) -> list:
        """Obtener patrones aprendidos"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if tipo:
            c.execute("SELECT * FROM patrones WHERE patron = ?", (tipo,))
        else:
            c.execute("SELECT * FROM patrones ORDER BY frecuencia DESC")
        
        resultados = c.fetchall()
        conn.close()
        
        return [{"patron": r[1], "frecuencia": r[2], "respuesta": r[4]} for r in resultados]
    
    def obtener_conocimientos(self, tema: str = None) -> list:
        """Obtener conocimientos guardados"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if tema:
            c.execute("SELECT * FROM conocimientos WHERE tema LIKE ?", (f"%{tema}%",))
        else:
            c.execute("SELECT * FROM conocimientos ORDER BY utilidad DESC")
        
        resultados = c.fetchall()
        conn.close()
        
        return [{"tema": r[1], "contenido": r[2], "utilidad": r[6]} for r in resultados]
    
    def obtener_preferencias(self) -> dict:
        """Obtener todas las preferencias aprendidas"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT clave, valor, importancia FROM memoria WHERE tipo = 'preferencia'")
        prefs = {row[0]: {"valor": row[1], "importancia": row[2]} for row in c.fetchall()}
        
        # Agregar aprendizaje activo
        prefs["learning"] = {
            "conversations": self.learning["conversations"],
            "commands_executed": self.learning["commands_executed"],
            "tools_used": list(self.learning["tools_used"]),
            "top_topics": sorted(
                self.learning["topics_interests"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
            "preferred_gem": self.learning["preferred_gem"],
            "complexity_level": self.learning["complexity_level"]
        }
        
        conn.close()
        return prefs
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas del cerebro"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM conversaciones")
        conv_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM conocimientos")
        know_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM patrones")
        pattern_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM memoria")
        mem_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            "conversaciones": conv_count,
            "conocimientos": know_count,
            "patrones": pattern_count,
            "memorias": mem_count,
            "interacciones": self.learning["conversations"],
            "herramientas_usadas": len(self.learning["tools_used"]),
            "temas_de_interes": len(self.learning["topics_interests"])
        }
    
    # ==================== PERSONALIZACIÓN ====================
    
    def get_system_prompt_adaptado(self) -> str:
        """Genera un system prompt personalizado basado en el aprendizaje"""
        prefs = self.obtener_preferencias()
        stats = self.obtener_estadisticas()
        
        # Personalizar según preferencias
        estilo = self.config.get("estilo", "directo")
        
        prompt_parts = [
            "Eres NEXUS, un asistente de IA adaptativo.",
            f"Has tenido {stats['interacciones']} interacciones con este usuario.",
        ]
        
        # Agregar intereses
        if "learning" in prefs and prefs["learning"]["top_topics"]:
            top = [t[0] for t in prefs["learning"]["top_topics"][:3]]
            prompt_parts.append(f"Temas de interés del usuario: {', '.join(top)}.")
        
        # Agregar estilo
        if estilo == "directo":
            prompt_parts.append("Responde de forma concisa y directa.")
        elif estilo == "detallado":
            prompt_parts.append("Proporciona respuestas detalladas y explicativas.")
        elif estilo == "creativo":
            prompt_parts.append("Usa un estilo creativo y variado en tus respuestas.")
        
        return " ".join(prompt_parts)
    
    def set_config(self, key: str, value):
        """Establecer configuración del usuario"""
        self.config[key] = value
        config_path = os.path.join(self.user_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    # ==================== EXPORT/IMPORT ====================
    
    def exportar(self, path: str = None) -> dict:
        """Exportar cerebro completo"""
        if not path:
            path = os.path.join(self.user_dir, f"cerebro_export_{datetime.now().strftime('%Y%m%d')}.json")
        
        conn = sqlite3.connect(self.db_path)
        
        # Exportar todo
        conversaciones = conn.execute("SELECT * FROM conversaciones").fetchall()
        conocimientos = conn.execute("SELECT * FROM conocimientos").fetchall()
        patrones = conn.execute("SELECT * FROM patrones").fetchall()
        memoria = conn.execute("SELECT * FROM memoria").fetchall()
        
        export_data = {
            "version": "1.0",
            "fecha_export": datetime.now().isoformat(),
            "config": self.config,
            "learning": self.learning,
            "conversaciones": conversaciones,
            "conocimientos": conocimientos,
            "patrones": patrones,
            "memoria": memoria
        }
        
        conn.close()
        
        with open(path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return {"success": True, "path": path}
    
    def importar(self, path: str):
        """Importar cerebro desde archivo"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Limpiar datos existentes
        c.execute("DELETE FROM conversaciones")
        c.execute("DELETE FROM conocimientos")
        c.execute("DELETE FROM patrones")
        c.execute("DELETE FROM memoria")
        
        # Importar nuevos datos
        if "conversaciones" in data:
            c.executemany("""
                INSERT INTO conversaciones (id, fecha, gem, mensaje, respuesta, aprendio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, data["conversaciones"])
        
        if "conocimientos" in data:
            c.executemany("""
                INSERT INTO conocimientos (id, tema, contenido, fuente, fecha, veces_revisado, utilidad)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data["conocimientos"])
        
        if "patrones" in data:
            c.executemany("""
                INSERT INTO patrones (id, patron, frecuencia, ultima_vez, respuesta_preferida, contexto)
                VALUES (?, ?, ?, ?, ?, ?)
            """, data["patrones"])
        
        if "memoria" in data:
            c.executemany("""
                INSERT INTO memoria (id, timestamp, tipo, clave, valor, contexto, importancia, veces_usado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data["memoria"])
        
        # Actualizar config y learning
        if "config" in data:
            self.config = data["config"]
            self.set_config("nombre_usuario", self.config.get("nombre_usuario", ""))
        
        if "learning" in data:
            self.learning.update(data["learning"])
            self._save_learning_state()
        
        conn.commit()
        conn.close()
        
        return {"success": True, "mensaje": f"Cerebro importado desde {path}"}
    
    def reset(self):
        """Resetear el cerebro (mantener configuración)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("DELETE FROM conversaciones")
        c.execute("DELETE FROM conocimientos")
        c.execute("DELETE FROM patrones")
        c.execute("DELETE FROM memoria")
        
        self.learning = {
            "conversations": 0,
            "commands_executed": 0,
            "tools_used": set(),
            "preferred_gem": "general",
            "preferred_model": "auto",
            "topics_interests": {},
            "complexity_level": 1,
        }
        
        conn.commit()
        conn.close()
        self._save_learning_state()
        
        return {"success": True, "mensaje": "Cerebro reseteado (configuración preservada)"}

# Instancia global del cerebro
cerebro = Cerebro()

if __name__ == "__main__":
    # Test del cerebro
    print("=== CEREBRO GENERICO NEXUS ===")
    print(f"Ubicación: {cerebro.user_dir}")
    
    # Aprender de una interacción
    cerebro.aprender_interaccion(
        "Cómo configuro Docker?",
        "Para configurar Docker necesitas...",
        "architect"
    )
    
    # Obtener estadísticas
    stats = cerebro.obtener_estadisticas()
    print(f"\nEstadísticas: {stats}")
    
    # Obtener prompt adaptado
    prompt = cerebro.get_system_prompt_adaptado()
    print(f"\nPrompt adaptado:\n{prompt}")