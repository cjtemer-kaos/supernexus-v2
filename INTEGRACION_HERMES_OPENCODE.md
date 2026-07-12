# 🔧 Integración Hermes Agent + OpenCode con SuperNEXUS v2

Guía completa para replicar el ecosistema local de IA: **Hermes Agent** (desktop chat) + **OpenCode** (CLI brain) + **SuperNEXUS v2** (23 gemas + 88 MCP tools).

---

## 📋 Requisitos Previos

| Componente | Versión mínima | Instalación |
|------------|---------------|-------------|
| Python | 3.10+ | [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o Python.org |
| Ollama | Latest | [ollama.com](https://ollama.com) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Hermes Agent | Latest | `pip install hermes-agent` o [hermes.nousresearch.com](https://hermes.nousresearch.com) |
| OpenCode | Latest | `npm install -g opencode` o [opencode.ai](https://opencode.ai) |

---

## 🚀 Paso 1: Instalar SuperNEXUS v2

```bash
# Clonar el repositorio
git clone https://github.com/cjtemer-kaos/supernexus-v2.git
cd supernexus-v2

# Instalar dependencias Python
pip install -r requirements.txt

# Crear archivo .env (copia del ejemplo)
cp .env.example .env
# Editar .env con tus valores (ver Paso 2)
```

---

## 🔑 Paso 2: Configurar .env

Edita el archivo `.env` en la raíz del proyecto:

```bash
# === OBLIGATORIO ===
NEXUS_PROJECT_DIR=/ruta/a/supernexus-v2    # Ruta absoluta al proyecto
OLLAMA_URL=http://localhost:11434           # URL de Ollama

# === OPCIONALES (para funcionalidad completa) ===
# API Keys de cloud (solo si usas modelos cloud)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# OpenCode Zen (modelos cloud gratuitos)
# Obtener key en: https://opencode.ai/auth
OPENCODE_API_KEY=

# Brave Search (para búsqueda web via MCP)
# Obtener key en: https://brave.com/search/api/
BRAVE_API_KEY=

# GitHub Personal Access Token
# Obtener en: GitHub Settings → Developer Settings → Personal Access Tokens
GITHUB_PERSONAL_ACCESS_TOKEN=

# Discord Bot (opcional)
DISCORD_TOKEN=
```

> ⚠️ **NUNCA subas tu `.env` a Git.** El `.gitignore` ya lo excluye.

---

## 🤖 Paso 3: Instalar Modelos Ollama

```bash
# Modelo principal (Director/ruteador) — siempre residente
ollama pull nexus-director-v6

# Modelos de código
ollama pull omnicoder-2-9b
ollama pull qwen2.5-coder:7b

# Modelos de razonamiento
ollama pull deepseek-r1:8b
ollama pull qwen3.5:9b

# Modelos de visión
ollama pull qwen2.5vl:7b
ollama pull gemma4:12b

# Modelo rápido
ollama pull nemotron-3-nano:4b

# Modelo ligero para resúmenes
ollama pull qwen2.5:0.5b

# Embeddings para RAG
ollama pull nomic-embed-text
```

### Presupuesto VRAM (RTX 3060 12GB)
- Director v6 (4.3GB) siempre residente
- Máximo 1-2 modelos adicionales simultáneos
- Usar `select_model` para routing óptimo

---

## 🔌 Paso 4: Configurar Hermes Agent

### 4.1 Instalar Hermes
```bash
pip install hermes-agent
```

### 4.2 Configurar SuperNEXUS como Provider
```bash
hermes config set providers.supernexus.type openai
hermes config set providers.supernexus.base_url http://localhost:9000/v1
hermes config set providers.supernexus.api_key none
hermes config set providers.supernexus.models '["nexus-director-v6"]'
```

### 4.3 Configurar MCP Bridge (SuperNEXUS → Hermes)
En `~/.hermes/config.yaml`, agregar:

```yaml
mcp:
  servers:
    supernexus:
      command: python
      args:
        - src/bridges/mcp_bridge_server.py
      env:
        NEXUS_PROJECT_DIR: /ruta/a/supernexus-v2
        NEXUS_BRAIN: /ruta/a/supernexus-v2/brain
```

### 4.4 Configurar Ollama como Provider adicional
```bash
hermes config set providers.ollama.type openai
hermes config set providers.ollama.base_url http://localhost:11434/v1
hermes config set providers.ollama.api_key ollama
```

---

## 💻 Paso 5: Configurar OpenCode

### 5.1 Instalar OpenCode
```bash
npm install -g opencode
```

### 5.2 Configurar Providers
En `~/.opencode/config.yaml`:

```yaml
providers:
  nexus:
    type: openai
    base_url: http://localhost:9000/v1
    api_key: none
    models:
      - nexus-director-v6

  ollama:
    type: openai
    base_url: http://localhost:11434/v1
    api_key: ollama

  zen:
    type: openai
    base_url: https://api.opencode.ai/v1
    api_key: ${OPENCODE_API_KEY}

mcp:
  servers:
    nexus-bridge:
      command: python
      args:
        - src/bridges/mcp_bridge_server.py
      env:
        NEXUS_PROJECT_DIR: /ruta/a/supernexus-v2
        NEXUS_BRAIN: /ruta/a/supernexus-v2/brain

    chrome-devtools:
      command: npx
      args:
        - chrome-devtools-mcp

    playwright:
      command: npx
      args:
        - "@playwright/mcp"

    context7:
      command: npx
      args:
        - "@upstash/context7-mcp"

    brave-search:
      command: npx
      args:
        - "@brave/brave-search-mcp"
      env:
        BRAVE_API_KEY: ${BRAVE_API_KEY}

    github:
      type: http
      url: https://api.githubcopilot.com/mcp/
      headers:
        Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}
```

---

## 🏗️ Paso 6: Iniciar SuperNEXUS

```bash
# Terminal 1: Servidor API (puerto 9000)
cd supernexus-v2
PYTHONPATH= python src/api/server.py

# Terminal 2: Ollama (ya debería estar corriendo)
ollama serve
```

### Verificar que funciona
```bash
# Test API
curl http://localhost:9000/health

# Test MCP Bridge
python -c "from src.bridges.mcp_bridge_server import brain_stats; print(brain_stats())"
```

---

## 🧠 Paso 7: Arquitectura del Ecosistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Ecosistema Local de IA                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Hermes Agent │  │   OpenCode   │  │ Claude Desktop│     │
│  │  (Desktop)    │  │   (CLI/TUI)  │  │  (Opcional)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         └──────────┬───────┴──────────┬───────┘               │
│                    │                  │                       │
│              ┌─────▼─────┐    ┌──────▼──────┐                │
│              │   MCP     │    │  REST API   │                │
│              │  Bridge   │    │  :9000      │                │
│              └─────┬─────┘    └──────┬──────┘                │
│                    │                  │                       │
│              ┌─────▼──────────────────▼──────┐               │
│              │       SuperNEXUS v2 Core       │               │
│              │  ┌─────────────────────────┐   │               │
│              │  │   DirectorNexus (22)    │   │               │
│              │  │   + Router + Brain      │   │               │
│              │  └─────────────────────────┘   │               │
│              │  ┌──────┐ ┌──────┐ ┌──────┐   │               │
│              │  │Scholar│ │ Sage │ │RAG   │   │               │
│              │  │ Gem  │ │ Gem  │ │Memory│   │               │
│              │  └──────┘ └──────┘ └──────┘   │               │
│              └───────────────┬───────────────┘               │
│                              │                               │
│              ┌───────────────▼───────────────┐               │
│              │         Ollama (11 modelos)    │               │
│              │  nexus-director-v6 | omnicoder │               │
│              │  deepseek-r1 | qwen3.5 | ...  │               │
│              └───────────────────────────────┘               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Docker:     │  │   Redis      │  │    n8n       │      │
│  │  Agent Zero  │  │   :6379      │  │   :5678      │      │
│  │  :50080      │  │  (PubSub)    │  │  (Workflows) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ MCP Tools Disponibles (88)

Al conectar via MCP Bridge, tienes acceso a:

### DirectorNexus Core
- `classify_task`, `execute_with_gema`, `run_agent_loop`, `run_harness`
- `get_director_status`, `change_project`, `get_relevant_skills`

### Memoria y Conocimiento
- `brain_remember` / `brain_recall` — cerebro persistente
- `add_observation` / `search_observations` — FTS5 memory
- `memory_set` / `memory_get` — memoria compartida KV

### Búsqueda Híbrida
- `retrieval_search` — vector + keyword + entities
- `memory_hierarchical_search` — 3 tiers con forgetting curves

### Multi-Agente
- `send_message` / `read_messages` — message board
- `spawn_sub_agent`, `mixture_of_agents`

### Redis PubSub (Real-time)
- `redis_publish` / `redis_get_messages`
- `redis_heartbeat` / `redis_list_agents`

### Calidad y Análisis
- `evaluate_quality`, `doctor_diagnose`, `router_select`

---

## 🔄 Protocolo al Iniciar Sesión

```python
# 1. Recall contexto general
brain_recall("general")

# 2. Si es tema técnico: búsqueda profunda
retrieval_search("tema")
search_observations("tema")

# 3. Al resolver algo: persistir aprendizaje
add_observation(topic_key="tema", content="lección aprendida")

# 4. Al finalizar tarea importante
brain_remember("lección: {tema}", contenido)
```

---

## 🐛 Solución de Problemas

### Ollama no responde
```bash
# Verificar que Ollama está corriendo
ollama list
curl http://localhost:11434/api/tags

# Reiniciar Ollama
ollama serve
```

### Puerto 9000 ocupado
```bash
# En Windows
netstat -ano | findstr :9000
taskkill /PID <PID> /F

# En Linux/Mac
lsof -i :9000
kill <PID>
```

### MCP Bridge no conecta
```bash
# Verificar que el path es correcto
cd supernexus-v2
python -c "from src.bridges.mcp_bridge_server import brain_stats; print(brain_stats())"

# Si falla, revisar NEXUS_PROJECT_DIR en .env
```

### Modelos no cargan en Ollama
```bash
# Verificar VRAM disponible
nvidia-smi

# Descargar modelo faltante
ollama pull <modelo>
```

---

## 📊 Comandos Útiles

```bash
# Estado del sistema
curl http://localhost:9000/api/status

# Listar modelos Ollama
ollama list

# Verificar MCP tools
python -c "from src.bridges.mcp_bridge_server import *; print('OK')"

# Ejecutar tests
cd supernexus-v2
python -m pytest --tb=short -q

# Diagnóstico completo
python -c "from src.core.doctor import Doctor; import asyncio; asyncio.run(Doctor().run())"
```

---

## 📚 Documentación Adicional

- [AGENTS.md](./AGENTS.md) — Reglas para agentes AI
- [BRAIN_ARCHITECTURE.md](./BRAIN_ARCHITECTURE.md) — Arquitectura del cerebro
- [INSTALL.md](./INSTALL.md) — Guía de instalación detallada
- [Hermes Docs](https://hermes-agent.nousresearch.com/docs) — Documentación oficial de Hermes
- [OpenCode Docs](https://opencode.ai/docs) — Documentación de OpenCode

---

## 🤝 Contribuir

Las mejoras al código son bienvenidas. Algunas áreas activas:
- Integración con más providers cloud
- Nuevas gemas especializadas
- Optimización de RAG
- Multi-agente orquestación

---

> **Nota:** Este ecosistema está diseñado para funcionar 100% local con Ollama. Las API keys cloud son opcionales para modelos premium.
