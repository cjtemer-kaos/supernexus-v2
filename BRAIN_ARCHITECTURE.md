# Arquitectura de Cerebros — SuperNEXUS + OpenCode

## Cerebro Unico Fusionado

El cerebro de SuperNEXUS y opencode estan fusionados en UNO SOLO.
Ambos acceden a los mismos archivos de base de datos en `brain/`.

## Estructura del Brain

```
${NEXUS_PROJECT_DIR}/brain/
  ├── cerebro.db              ← Brain persistente (117+ keys)
  │     • brain_remember / brain_recall
  │     • conocimiento aprendido entre sesiones
  │     • patrones, preferencias, lecciones
  │
  ├── nexus_memory.db         ← Memoria FTS5 (observations + findings)
  │     • add_observation / search_observations
  │     • busqueda full-text
  │     • topic_key para UPSERT (evita duplicados)
  │     • grafos de relacion entre observaciones
  │
  ├── message_board.db        ← NexusHive message board
  │     • send_message / read_messages
  │     • comunicacion entre agentes en tiempo real
  │
  ├── learning.json           ← Metricas de aprendizaje
  │     • conversaciones contadas
  │     • herramientas usadas
  │     • intereses detectados
  │
  ├── learnings.md            ← Lecciones en texto plano
  │
  └── backups/                ← Backups automaticos
```

## Las 4 Capas de Memoria

### Capa 1: HierarchicalMemory (3 tiers)
**Archivo**: `~/.nexus/hierarchical_memory.json`
- **WORKING**: 1h de vida util, capacidad 100 items
- **EPISODIC**: 72h de vida util, capacidad 500 items
- **SEMANTIC**: 1 anio de vida util, capacidad ilimitada
- **Forgetting curves**: decay_score = recency * 0.7 + frequency * 0.3
- **Auto-promocion**: items accedidos frecuentemente suben de tier

### Capa 2: RAG Engine (Vector Search)
**Archivo**: `~/.nexus/rag_index.db`
- Embeddings con `nomic-embed-text` (274MB, 768d)
- Chunking: 800 chars con overlap de 100
- Cache MD5 de embeddings para evitar recomputar
- Cosine similarity para busqueda semantica

### Capa 3: MultiSignalRetrieval (Busqueda Hibrida)
**Fusiona 3 senales**:
1. **Vector** (RAG semantico) — "que significa?"
2. **Keyword** (FTS5/BM25) — "donde aparece exactamente?"
3. **Entities** (extraccion de nombres) — "quien/que menciona?"

### Capa 4: SelfLearningLoop (Auto-aprendizaje)
- Loop cada 120s
- Evalua calidad de respuestas (judge)
- Alimenta AdaptiveRouter (Thompson Sampling)
- Extrae patrones de exito/fracaso

## Integracion con OpenCode

### Como opencode usa el cerebro

```python
# 1. Al iniciar: cargar contexto general
brain_recall("general")

# 2. En consulta tecnica: busqueda semantica
retrieval_search(query)     # 3 senales
search_observations(query)  # FTS5 directo

# 3. Despues de aprender: guardar
add_observation(content, topic_key="...")
brain_remember("leccion: {tema}", contenido)

# 4. Al completar tarea
add_task_finding(tarea, resultado)
```

### Como configurar NEXUS_BRAIN

```bash
# En Windows (PowerShell como Admin):
[Environment]::SetEnvironmentVariable("NEXUS_BRAIN", "D:\supernexus-v2\brain", "User")

# En Linux (~/.bashrc o ~/.zshrc):
export NEXUS_BRAIN=/home/user/supernexus-v2/brain

# O en el script de inicio (start_server.py):
os.environ["NEXUS_BRAIN"] = os.path.join(PROJECT_DIR, "brain")
```

## Flujo de Datos

```
OpenCode (pregunta)
    │
    ├─► brain_recall() ───────────► cerebro.db
    ├─► retrieval_search() ───────► RAG + FTS5 + Entities
    ├─► search_observations() ────► nexus_memory.db
    │
    ▼
Respuesta con contexto enriquecido
    │
    ├─► add_observation() ────────► nexus_memory.db
    ├─► brain_remember() ─────────► cerebro.db
    └─► add_task_finding() ───────► nexus_memory.db
```

## Persistencia en Git

`/brain/` esta en `.gitignore` — el cerebro NO se sube a GitHub.
Cada maquina construye su propio cerebro con el uso.
El `.env.example` contiene las claves para que opencode sepa donde esta el brain.
