# MCP Tools Integradas

## 1. nexus-sovereign (CRITICAL — Bridge Python)
**Archivo**: `src/bridges/mcp_bridge_server.py` (38 tools)
**Conexion**: stdio via opencode.json

Tool categories:
- **Memoria**: add_observation, search_observations, get_observation, delete_observation, relate_observations
- **Brain**: brain_remember, brain_recall, brain_stats
- **Message Board**: send_message, read_messages
- **Orquestacion**: classify_task, execute_with_gema, run_harness, run_agent_loop
- **Multi-Agente**: mixture_of_agents, parallel_execute
- **Skills**: list_skills, load_skill, load_skill_section
- **RAG**: rag_index, rag_search, rag_stats
- **Router**: router_select, router_stats
- **Sistema**: nexus_status, system_resources, doctor_diagnose
- **Autodiagnostico**: detect_prompt_injection, system_security_scan
- **PC Remoto**: execute_on_remote_node, list_nodes, get_system_info
- **Busqueda Hibrida**: retrieval_search (vector+keyword+entities)
- **Memoria Jerarquica**: memory_hierarchical_store/search/stats
- **Auto-aprendizaje**: self_learning_status
- **Cerebro Compartido**: memory_set, memory_get

## 2. chrome-devtools
**Comando**: `npx chrome-devtools-mcp@latest --browserUrl http://127.0.0.1:9222`
**Tools**: 38 tools para automation de Chrome via CDP
- navegacion, click, type, snapshot, screenshot
- evaluacion JS, performance tracing, network requests
- console messages, lighthouse audit, heap snapshots
- Requiere Chrome con `--remote-debugging-port=9222`
- **Deshabilitado por defecto** — habilitar en opencode.json cuando se necesite

## 3. playwright
**Comando**: `npx @playwright/mcp@latest`
**Tools**: Browser automation via Playwright
- **Deshabilitado por defecto** — alternativa mas pesada a chrome-devtools

## 4. context7
**Comando**: `npx @upstash/context7-mcp`
**Tools**: Documentacion live de librerias/frameworks
- Busca docs actualizados de React, Next.js, Prisma, Django, etc.
- **Habilitado por defecto**

## 5. brave-search
**Comando**: `npx @brave/brave-search-mcp-server`
**Requiere**: `BRAVE_API_KEY` en env vars
**Tools**: Busqueda web, imagenes, noticias, videos, locales
- **Habilitado por defecto**

## 6. github
**Tipo**: Remote (HTTP)
**URL**: `https://api.githubcopilot.com/mcp/`
**Requiere**: `GITHUB_PERSONAL_ACCESS_TOKEN` en env vars
**Tools**: PRs, issues, repos, reviews
- **Habilitado por defecto**

## 7. agent-browser
**Archivo**: `src/bridges/agent_browser_mcp.py` (Python)
**Comando**: Python ligero con playwright
**Tools**: Busqueda web rapida, navegacion simple
- **Habilitado por defecto**

---

## Resumen de Estado

| MCP Server | Estado | Tipo | Dependencia |
|------------|--------|------|-------------|
| nexus-sovereign | ✅ ACTIVO | local (Python) | NEXUS_BRAIN, PYTHONPATH |
| chrome-devtools | ❌ Desactivado | local (npx) | Chrome :9222 |
| playwright | ❌ Desactivado | local (npx) | Playwright browsers |
| context7 | ✅ ACTIVO | local (npx) | — |
| brave-search | ✅ ACTIVO | local (npx) | BRAVE_API_KEY |
| github | ✅ ACTIVO | remote (HTTP) | GITHUB_TOKEN |
| agent-browser | ✅ ACTIVO | local (Python) | Python playwright |

## Configuracion en opencode.json
Los MCP se configuran en `~/.config/opencode/opencode.json`.
Ver `opencode.json.example` en la raiz del proyecto.
