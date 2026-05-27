# SuperNEXUS v2.1 — Ecosistema de IA Autónomo Local

Sistema de IA sovereign que integra 22 agentes especializados (gemas), pipeline de entrenamiento SFT/DPO, RAG semántico, interfaz de voz (JARVIS), y loops autónomos multi-agente. 100% local con Ollama.

## Arquitectura

```
SuperNEXUS v2.1
│
├── 🧠 DirectorNexus (Cerebro Central)
│   ├── 22 Gemas especializados
│   ├── Harness Engineering (compaction, hooks, memory, skills)
│   ├── Multi-agent (sub-agents, mixture of agents)
│   ├── CodeGraph AST analysis
│   └── Judge pipeline (calidad 3 niveles)
│
├── 🔌 Connectivity
│   ├── API REST (171 endpoints, aiohttp)
│   ├── MCP Bridge (18 tools, stdio + SSE)
│   ├── SSH Bridge (conexión remota)
│   ├── NexusHive (message_board, agentes autónomos)
│   └── CDP Browser (Chrome DevTools Protocol)
│
├── 💾 Memoria 3 Capas + RAG
│   ├── Capa 1: SQLite Neural Patterns
│   ├── Capa 2: RAG Semántico (nomic-embed-text, 768d)
│   ├── Capa 3: Knowledge Graph
│   ├── FTS5 Observations
│   └── Shared Brain
│
├── 🎓 Entrenamiento
│   ├── SFT (Supervised Fine-Tuning con TRL)
│   ├── DPO (Direct Preference Optimization)
│   ├── PeerChat distribuido
│   └── Recolección de samples automatizada
│
├── 🗣️ Voz (JARVIS Mark XXXIX)
│   ├── STT: whisper + VAD
│   ├── TTS: Piper
│   ├── LLM: compatible con Ollama
│   └── API HTTP dedicada
│
├── 🤖 Agentes Autónomos
│   ├── zero-code — Agent Zero (Docker)
│   ├── hermes-code — Hermes CLI
│   ├── jarvis-code — JARVIS API
│   └── qwen-code — Qwen loop
│
├── 🖥️ Desktop UI (Electron + React + Vite)
│   ├── 22 gemas seleccionables
│   ├── Chat con streaming + attachments
│   ├── Monitor de sistema (CPU/RAM/GPU/Disco)
│   ├── Avatar 3D
│   ├── NexusHive en tiempo real
│   └── Settings persistente
│
└── 🐳 Docker Services (opcional)
    ├── Agent Zero — sandbox Python
    ├── Redis — cache
    └── n8n — automation
```

## 22 Gemas

| Gema | Capacidad |
|------|-----------|
| director | Orquestación, DAG, planning |
| code | Programación, refactoring |
| scholar | Research, web search |
| architect | System design |
| creative | Contenido creativo |
| sage | Memoria, persistencia |
| analyst | Data analysis |
| engineer | Ingeniería, tools |
| debugger | Debugging |
| optimizer | Performance |
| tester | Testing, QA |
| security | Security audit |
| devops | Deploy, infra |
| trainer | Training |
| biblioteca | Knowledge mgmt |
| vision | Screenshot, OCR |
| opencode | CLI agent |
| codex | Code delegation |
| design | UI/UX |
| music | Audio, TTS |
| prompter | Prompt optimization |
| producer | Automation |

## Requisitos

- Python 3.10+
- Ollama con modelos: gemma4, deepseek-r1, qwen2.5-coder, nemotron-3-nano, nomic-embed-text
- Node.js 18+ (solo para UI)
- GPU NVIDIA 6GB+ VRAM (recomendado)

## Instalación

```bash
pip install -r requirements.txt
cd ui && npm install
```

## Uso

```bash
# Backend API (puerto 9000)
python -m src.api.server 9000

# Desktop UI (desarrollo)
cd ui && npm run dev

# Desktop UI (producción)
cd ui && npm run build:electron

# JARVIS voice interface (puerto 9039)
python /ruta/a/jarvis/main.py
```

## Conexiones por Defecto

| Servicio | Puerto |
|----------|--------|
| SuperNEXUS API | 9000 |
| JARVIS Voice | 9039 |
| Agent Zero | 50080 |
| MCP Bridge SSE | 9010 |
| Ollama | 11434 |

## Modelos Ollama Recomendados

| Modelo | Uso |
|--------|-----|
| gemma4:latest | General, creative (128K ctx) |
| deepseek-r1:8b | Reasoning, research |
| qwen2.5-coder:7b | Coding, engineering |
| qwen2.5vl:7b | Vision |
| nemotron-3-nano:4b | Fast analysis |
| nomic-embed-text | Embeddings (RAG) |

## Estructura del Proyecto

```
supernexus-v2/
├── main.py                    # Entry point
├── supernexus/                # Paquete principal
│   ├── __init__.py            # Versión
│   └── __main__.py            # python -m supernexus
├── src/
│   ├── core/                  # Lógica central
│   │   ├── director.py        # DirectorNexus
│   │   ├── server.py          # API REST
│   │   └── ...                # 96+ módulos
│   ├── agents/                # Loops autónomos
│   ├── bridges/               # MCP, SSH, conexiones
│   ├── memory/                # Sistemas de memoria
│   ├── tools/                 # Herramientas
│   └── skills/                # Skills registry
├── ui/                        # Electron + React
│   ├── apps/
│   │   ├── main/              # Electron main process
│   │   ├── preload/           # Security bridge
│   │   └── renderer/          # React (Vite)
│   └── package.json
├── deploy/                    # Scripts de deploy
├── scripts/                   # Utilidades
└── tests/                     # Tests
```

## Zero Secrets

SuperNEXUS nunca almacena secretos en el código. Usa variables de entorno para credenciales externas.
