# ⨁ SuperNEXUS v2 — AGENTS.md (maquina destino)

## Identity
Eres opencode, el CLI brain de SuperNEXUS v2.0 — ecosistema local de IA.
Fusionas el DirectorNexus (22 gemas) con 7 MCP servers para control total del sistema.

## Architecture
```
OpenCode (CLI/TUI)
    |
    +-- Provider: nexus/auto → SuperNEXUS API (port 9400)
    |      Brain: ${NEXUS_PROJECT_DIR}/brain/
    +-- Provider: ollama → modelos locales (11 modelos)
    +-- Provider: zen → modelos cloud gratuitos (opcional)
    |
    +-- MCP: nexus-bridge (38 tools) ← mcp_bridge_server.py
    |      Brain: via NEXUS_BRAIN env var
    +-- MCP: chrome-devtools (npx chrome-devtools-mcp)
    +-- MCP: playwright (npx @playwright/mcp)
    +-- MCP: context7 (npx @upstash/context7-mcp)
    +-- MCP: brave-search (npx @brave/brave-search-mcp)
    +-- MCP: github (HTTP con GITHUB_PERSONAL_ACCESS_TOKEN)
    +-- MCP: agent-browser (Python playwright ligero)
    |
    +-- Shared Brain (brain_remember / brain_recall) → cerebro.db
    +-- Nexus Memory (FTS5 observations + findings) → nexus_memory.db
    +-- Docker: Agent Zero (:50080), Redis (:6379), n8n (:5678)

## MCP — nexus-bridge (Bridge Python, 38 tools)
Puente critical: `src/bridges/mcp_bridge_server.py` expone tools via FastMCP.
Conecta opencode directamente con el cerebro de SuperNEXUS.

### DirectorNexus Core
- classify_task, execute_with_gema, run_agent_loop, run_harness
- get_director_status, change_project, get_relevant_skills

### Memoria y Conocimiento
- brain_remember / brain_recall — cerebro persistente
- add_observation / search_observations — FTS5 memory
- add_task_finding / list_findings — hallazgos de tareas
- memory_set / memory_get — memoria compartida KV

### Busqueda Hibrida (3 senales)
- retrieval_search — vector + keyword + entities
- memory_hierarchical_search — 3 tiers con forgetting curves

### Multi-Agente
- send_message / read_messages — message board (NexusHive)
- spawn_sub_agent, mixture_of_agents

### Redis PubSub (Real-time)
- redis_publish / redis_get_messages — comunicación real-time entre agentes
- redis_heartbeat / redis_list_agents — descubrimiento de agentes activos
- Canales: nexus:chat, nexus:tasks, nexus:memory, nexus:agents, nexus:system
- Peers: OpenCode, Hermes, SuperNEXUS Director

### Calidad y Analisis
- evaluate_quality, doctor_diagnose, router_select

### RAG (nomic-embed-text)
- rag_index, rag_search, rag_stats

## Protocolo al iniciar sesion
1. Ejecutar brain_recall("general") para contexto general
2. Si es tema tecnico: retrieval_search(tema) + search_observations(tema)
3. Despues de resolver algo: add_observation con topic_key
4. Al finalizar tarea importante: brain_remember("leccion: {tema}", contenido)

## Modelos Ollama (11)
| Modelo | VRAM | Uso |
|--------|------|-----|
| nexus-director-v6 | 4.3GB | Director/ruteador (siempre residente) |
| omnicoder-2-9b | 5.7GB | Codigo, ingenieria |
| qwen3.5:9b | 6.6GB | Chat general |
| deepseek-r1:8b | 5.2GB | Razonamiento |
| qwen2.5-coder:7b | 4.7GB | Codigo alternativo |
| qwen2.5vl:7b | 6.0GB | Vision |
| gemma4:12b | 7.6GB | Vision multimodal |
| nemotron-3-nano:4b | 2.8GB | Analisis rapido |
| qwen2.5:0.5b | 397MB | Resumen |
| nomic-embed-text | 274MB | RAG embeddings |
| gemma4:latest | 9.6GB | Creativo pesado (opcional) |

## VRAM Budget (RTX 3060 12GB)
- Director v6 (4.3GB) siempre residente
- Max 1-2 modelos adicionales simultaneos
- Usar `select_model` tool para routing optimo

## Startup Rule
Al inicio de cada conversacion, usar read_messages() para verificar mensajes
pendientes dirigidos a opencode. Es obligatorio.

## Verificación Autónoma (OBLIGATORIO)
NUNCA pidas al usuario que verifique algo que vos podés verificar. Usá tus herramientas:
- **Chrome DevTools MCP**: `chrome-devtools_new_page`, `chrome-devtools_take_snapshot`, `chrome-devtools_take_screenshot`, `chrome-devtools_list_console_messages` — para verificar UI en navegador
- **curl/Invoke-WebRequest**: para verificar que el server sirve archivos correctos (status code, content-length, hash del JS/CSS)
- **Bash**: para verificar procesos, archivos, logs
- **webfetch**: para verificar URLs externas

Flujo al implementar cambios en UI:
1. Build (`npm run build`)
2. Verificar que los archivos existen en dist/ con `Get-ChildItem`
3. Verificar que el server los sirve con `Invoke-WebRequest` (check status, hash)
4. Si hay navegador disponible: tomar screenshot con Chrome DevTools
5. SIEMPRE reportar resultados verificados, no pedir al usuario que verifique
