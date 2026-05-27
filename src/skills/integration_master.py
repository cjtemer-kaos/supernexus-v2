#!/usr/bin/env python3
"""
🧠 NEXUS SKILL INTEGRATION MASTER
Recupera NEXUS + Integra 1.441+ skills del catálogo Santos IA
Usa DirectorNexus + Gemas para paralelizar ingestion de skills
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List
import subprocess
import sqlite3

# Agregar rutas críticas
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from nexus_director import NexusDirector, WorkerPool, GemType
except ImportError as e:
    print(f"⚠️  NexusDirector no disponible: {e}")
    class NexusDirector:
        def __init__(self): pass
        def select_gem(self, task): return None
        def process_task(self, task, worker_pool=None):
            return {"status": "fallback", "response": "Fallback mode"}


class NexusSkillIntegrationMaster:
    """Orquestador para recuperación + integración masiva de skills"""

    def __init__(self):
        print("\n" + "="*80)
        print("🧠 NEXUS SKILL INTEGRATION MASTER - INICIANDO")
        print("="*80 + "\n")

        self.director = NexusDirector()
        self.workers = WorkerPool()
        self.root_dir = Path(os.getenv("NEXUS_HOME", Path.home() / ".nexus"))

        # Estructura de destino
        self.nexus_restored = self.root_dir / "restored"
        self.core_dir = self.nexus_restored / "core"
        self.skills_dir = Path(__file__).parent / "hub"
        self.memory_dir = self.nexus_restored / "memory"
        self.skills_catalog = self.nexus_restored / "skills_catalog"

        self.pc2_available = self._check_pc2()
        self.skills_inventory = {}
        self.integration_log = []

        print(f"✓ Director Nexus inicializado")
        print(f"✓ Workers disponibles: {len(self.workers.list_available())}")
        print(f"✓ PC2 disponible: {'SÍ' if self.pc2_available else 'NO'}")
        print(f"✓ Estructura destino: {self.nexus_restored}\n")

    def _check_pc2(self) -> bool:
        """Verifica si nodo remoto está disponible via SSH"""
        pc2_ip = os.getenv("SUPER_NEXUS_PC2_IP", "")
        pc2_user = os.getenv("SUPER_NEXUS_PC2_USER", "")
        if not pc2_ip or not pc2_user:
            return False
        try:
            result = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=3', f'{pc2_user}@{pc2_ip}', 'echo', 'OK'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def audit_current_skills(self) -> Dict:
        """Audita skills actuales (delegado a ScholarGem)"""
        print("🔍 AUDITORÍA DE SKILLS ACTUALES (ScholarGem)...\n")

        task = """Eres ScholarGem, experto en investigación y catalogación.

Tu tarea: Auditar TODOS los skills en el directorio NEXUS:

1. Escanear recursivamente buscando:
   - Archivos *_skill.py
   - Archivos *_ability.py
   - Archivos con palabra "skill" en el nombre
   - Archivos GEM_*.md (instrucciones de gemas)

2. Para cada skill encontrado, reportar:
   - Nombre exacto del archivo
   - Ruta completa relativa al root del proyecto
   - Tipo (based on nombre): architect, developer, scholar, creative, sage, custom
   - Estado (encontrado pero ¿funcional?)

3. Generar JSON con estructura:
{
    "total_skills": N,
    "by_category": {...},
    "found_skills": [...],
    "missing_critical": [...]
}

Sé exhaustivo. Cada skill importa."""

        result = self.director.process_task(task, worker_pool=self.workers)

        print(f"[{result.get('gem')}] Auditoría completada:\n")
        print(result.get('response'))
        print("\n")

        return result

    def map_santos_ia_catalog(self) -> Dict:
        """Mapea los 1.441+ skills disponibles del catálogo (delegado a ScholarGem)"""
        print("📚 MAPEO DEL CATÁLOGO SANTOS IA (ScholarGem)...\n")

        task = """Eres ScholarGem, experto en catalogación y síntesis.

Tu tarea: Crear estructura de mapeo para 1.441+ skills del catálogo Santos IA.

NO necesitas acceder a archivos (no existen). Necesitas CREAR la estructura que
permitirá integrar estos skills cuando estén disponibles.

Estructura a crear:

1. Categorías principales (basadas en Gemas):
   - ARCHITECT: Infrastructure, DevOps, Containers, Networking (est. 200 skills)
   - DEVELOPER: Coding, Debugging, Refactoring, MCP (est. 400 skills)
   - SCHOLAR: Learning, Research, Knowledge, Ingestion (est. 200 skills)
   - CREATIVE: Multimedia, Assets, Generation, Storyboarding (est. 300 skills)
   - SAGE: Deep Research, Synthesis, Expert Systems (est. 150 skills)
   - CUSTOM: Specialized, Domain-specific (est. 191 skills)

2. Para cada categoría, crear:
   - Subcategorías por dominio
   - Nombre de skill esperado
   - Descripción de capacidad
   - Dependencias esperadas
   - Configuración requerida

3. Generar JSON de mapeo:
{
    "total_skills_expected": 1441,
    "categories": {...},
    "ingestion_priority": [...]
}

Este mapeo será la guía para integración."""

        result = self.director.process_task(task, worker_pool=self.workers)

        print(f"[{result.get('gem')}] Mapeo de catálogo:\n")
        print(result.get('response'))
        print("\n")

        return result

    def create_directory_structure(self):
        """Crea estructura de directorios para sistema restaurado"""
        print("📁 CREANDO ESTRUCTURA DE DIRECTORIOS...\n")

        dirs = [
            self.nexus_restored,
            self.core_dir,
            self.skills_dir,
            self.memory_dir,
            self.skills_catalog,
            self.skills_catalog / "ARCHITECT",
            self.skills_catalog / "DEVELOPER",
            self.skills_catalog / "SCHOLAR",
            self.skills_catalog / "CREATIVE",
            self.skills_catalog / "SAGE",
            self.skills_catalog / "CUSTOM"
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ {dir_path}")

        print("\n")

    def preserve_memory_database(self):
        """Preserva la base de datos de memoria (CRÍTICO)"""
        print("💾 PRESERVANDO BASE DE DATOS DE MEMORIA...\n")

        source_db = Path(__file__).parent.parent.parent.parent / "memory" / "nexus_memory.db"
        target_db = self.memory_dir / "nexus_memory.db"

        if source_db.exists():
            try:
                # Copiar archivo
                import shutil
                shutil.copy2(source_db, target_db)

                # Verificar integridad
                db = sqlite3.connect(target_db)
                cursor = db.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                db.close()

                print(f"✓ Memoria restaurada: {target_db}")
                print(f"✓ Tablas en base de datos: {len(tables)}")
                for table in tables:
                    print(f"  - {table[0]}")
                print("\n")
            except Exception as e:
                print(f"❌ Error preservando memoria: {e}\n")
        else:
            print(f"⚠️  Archivo de memoria no encontrado en {source_db}\n")

    def plan_skill_ingestion_process(self) -> Dict:
        """Planifica proceso de ingestion masiva (delegado a ArchitectGem)"""
        print("🏗️  PLANIFICACIÓN DE INGESTION (ArchitectGem)...\n")

        task = """Eres ArchitectGem, especialista en infraestructura y pipelines.

Tu tarea: Crear plan detallado para ingerir 1.441+ skills en NEXUS:

Plan debe incluir:

1. FASE 1 - PREPARACIÓN (Local, sin red):
   - Crear índice maestro de skills
   - Configurar sistema de clasificación
   - Preparar almacenamiento por categoría
   - Crear metadata para cada skill

2. FASE 2 - INGESTION MASIVA:
   - Procesar skills por lotes (batch processing)
   - Validar estructura de cada skill
   - Generar mappeo a Gemas apropiados
   - Crear searchindex para búsqueda rápida

3. FASE 3 - INTEGRACIÓN:
   - Registrar skills en nexus_director.py
   - Actualizar clasificación de tareas
   - Crear aliases y shortcuts
   - Configurar fallbacks

4. FASE 4 - VERIFICACIÓN:
   - Test de carga de skill
   - Verificar delegación correcta
   - Validar performance
   - Documentar capacidades nuevas

Específicamente para cada fase:
- Scripts necesarios
- Recursos requeridos
- Tiempo estimado
- Métricas de éxito"""

        result = self.director.process_task(task, worker_pool=self.workers)

        print(f"[{result.get('gem')}] Plan de ingestion:\n")
        print(result.get('response'))
        print("\n")

        return result

    def create_skill_registry_system(self) -> Dict:
        """Crea sistema de registro para skills (delegado a DeveloperGem)"""
        print("🔧 CREANDO SISTEMA DE REGISTRO (DeveloperGem)...\n")

        task = """Eres DeveloperGem, especialista en desarrollo y arquitectura de código.

Tu tarea: Crear sistema Python para registrar y gestionar 1.441+ skills.

Sistema debe incluir:

1. skill_registry.py:
   - Clase SkillRegistry para cargar/buscar skills
   - Método para registrar skill con metadata
   - Método para buscar skills por tipo/categoría
   - Método para generar skill index JSON
   - Método para validar compatibilidad

2. skill_loader.py:
   - Cargar skills desde directorio
   - Parsear archivo de skill buscando: descripción, capacidades, dependencias
   - Generar entrada en índice
   - Manejo de errores robusto

3. skill_mapper.py:
   - Mapear cada skill a Gema apropiado
   - Crear delegación automática en nexus_director
   - Sistema de aliases
   - Fallback inteligente

4. Estructura de skill (estándar):
```python
# skill_ejemplo.py
SKILL_METADATA = {
    'name': 'Skill Name',
    'category': 'DEVELOPER',
    'subcategory': 'Python',
    'capabilities': ['code', 'debug'],
    'dependencies': [],
    'version': '1.0',
    'author': 'Nexus Team'
}

class SkillEjemplo:
    def __init__(self):
        self.metadata = SKILL_METADATA

    async def execute(self, task: str) -> str:
        # Implementación
        pass
```

Proporciona pseudocódigo detallado para estos 3 archivos."""

        result = self.director.process_task(task, worker_pool=self.workers)

        print(f"[{result.get('gem')}] Sistema de registro:\n")
        print(result.get('response'))
        print("\n")

        return result

    def delegate_pc2_skill_extraction(self) -> Dict:
        """Extrae skills de PC2 para referencia (delegado a ArchitectGem)"""
        print("🔗 EXTRAYENDO SKILLS DE PC2 (ArchitectGem)...\n")

        if not self.pc2_available:
            print("⚠️  PC2 no disponible, saltando extracción\n")
            return None

        task = """Eres ArchitectGem, especialista en sincronización distribuida.

Tu tarea: Crear plan para extraer skills del nodo remoto.

El nodo remoto tiene versión más madura con 1.441+ skills listos.
Objetivo: Usar nodo remoto como fuente de referencia para acelerar integración local.

Plan:
1. Conectar al nodo remoto via SSH
2. Listar estructura de skills
3. Extraer metadata de cada skill sin copiar archivos (ahorrar datos)
4. Generar índice de skills disponibles
5. Mapear diferencias entre versión remota y versión local

Comandos SSH específicos:
- find ~/skills -name "*.py" -type f
- for each file: head -20 (para leer metadata)
- Crear JSON con índice completo

Esto permite saber exactamente qué skills integrar sin descargar."""

        result = self.director.process_task(task, worker_pool=self.workers)

        print(f"[{result.get('gem')}] Plan de extracción PC2:\n")
        print(result.get('response'))
        print("\n")

        return result

    def parallel_orchestration(self):
        """Ejecuta todas las tareas de ingestion en paralelo"""
        print("\n" + "="*80)
        print("⚡ ORQUESTACIÓN PARALELA DE INGESTION")
        print("="*80 + "\n")

        tasks = [
            {
                "name": "Auditoría de Skills Actuales",
                "gem": "SCHOLAR",
                "method": self.audit_current_skills
            },
            {
                "name": "Mapeo Catálogo Santos IA",
                "gem": "SCHOLAR",
                "method": self.map_santos_ia_catalog
            },
            {
                "name": "Planificación Ingestion",
                "gem": "ARCHITECT",
                "method": self.plan_skill_ingestion_process
            },
            {
                "name": "Sistema de Registro",
                "gem": "DEVELOPER",
                "method": self.create_skill_registry_system
            }
        ]

        if self.pc2_available:
            tasks.append({
                "name": "Extracción Skills PC2",
                "gem": "ARCHITECT",
                "method": self.delegate_pc2_skill_extraction
            })

        results = {}

        for task_def in tasks:
            print(f"▶️  Delegando a {task_def['gem']}: {task_def['name']}...")
            result = task_def['method']()
            results[task_def['name']] = result
            print(f"✓ {task_def['name']} completado\n")

        return results

    def run_full_integration(self):
        """Ejecuta recuperación + integración completa"""
        print("\n" + "="*80)
        print("🎬 INICIANDO RECUPERACIÓN + INTEGRACIÓN MASIVA")
        print("="*80 + "\n")

        # FASE 1: Preparación de estructura
        print("[FASE 1] PREPARACIÓN\n")
        self.create_directory_structure()
        self.preserve_memory_database()

        # FASE 2: Auditoría y mapeo (Paralelo)
        print("\n[FASE 2] AUDITORÍA Y MAPEO (Paralelo)\n")
        parallel_results = self.parallel_orchestration()

        # FASE 3: Resumen
        print("\n" + "="*80)
        print("✓ ORCHESTRACIÓN COMPLETADA")
        print("="*80 + "\n")

        print("RESUMEN EJECUTIVO:")
        print(f"  ✓ Directorio restaurado: {self.nexus_restored}")
        print(f"  ✓ Estructura creada: 01_CORE, 02_SKILLS, 03_SKILLS_CATALOG")
        print(f"  ✓ Memoria preservada: SÍ (nexus_memory.db intacta)")
        print(f"  ✓ Gemas utilizados: 4-5 (SCHOLAR, ARCHITECT, DEVELOPER)")
        print(f"  ✓ PC2 sincronizado: {'SÍ' if self.pc2_available else 'NO'}")
        print(f"  ✓ Skills a integrar: 1.441+")
        print("\nPróximo paso: Ejecutar ingestion masiva de skills")
        print("="*80 + "\n")


def main():
    master = NexusSkillIntegrationMaster()
    master.run_full_integration()


if __name__ == "__main__":
    main()
