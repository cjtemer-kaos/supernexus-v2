# Guia de Instalacion — SuperNEXUS v2 Distro

## Requisitos del Sistema
- **GPU**: NVIDIA RTX 3060 12GB VRAM (o similar)
- **RAM**: 16GB+ (32GB recomendado)
- **Disco**: 50GB+ libres (modelos Ollama ~40GB)
- **SO**: Windows 10/11 o Linux (Ubuntu 22.04+)
- **Python**: 3.10+
- **Node.js**: 18+ (solo para UI)
- **Docker**: Para servicios opcionales (Agent Zero, Redis, n8n)

---

## 1. Instalar Ollama

```bash
# Windows: Descargar de https://ollama.com/download
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh
```

## 2. Descargar Modelos Ollama

Ejecutar el script de instalacion de modelos:

```bash
# Linux/Mac
chmod +x install_ollama_models.sh
./install_ollama_models.sh

# Windows Powershell
.\install_ollama_models.ps1
```

### Lista completa de modelos (11, ~40GB total):

| Modelo | Tamano | Uso |
|--------|--------|-----|
| `nexus-director-v6:latest` | 4.3 GB | **CEREBRO** — Director/ruteador (instalacion especial, ver abajo) |
| `omnicoder-2-9b:q4_k_m` | 5.7 GB | Codigo, ingenieria (gema code, architect, engineer...) |
| `qwen3.5:9b` | 6.6 GB | Chat general, creative |
| `deepseek-r1:8b` | 5.2 GB | Razonamiento, investigacion (gema scholar, sage, debugger...) |
| `qwen2.5-coder:7b` | 4.7 GB | Codigo alternativo |
| `qwen2.5vl:7b` | 6.0 GB | Vision (gema vision) |
| `gemma4:12b` | 7.6 GB | Vision, multimodal (256K ctx) |
| `nemotron-3-nano:4b` | 2.8 GB | Analisis rapido (gema analyst) |
| `qwen2.5:0.5b` | 397 MB | Resumen ultra-rapido |
| `nomic-embed-text` | 274 MB | **OBLIGATORIO** — Embeddings para RAG |
| `gemma4:latest` | 9.6 GB | Creativo pesado (128K ctx) — opcional |

**Importante**: En RTX 3060 12GB, el Director v6 (4.3GB) debe estar siempre residente. Solo puedes cargar 1-2 modelos adicionales a la vez.

### Instalacion del Director v6

El Director v6 es un modelo custom fine-tuned con QLoRA sobre Qwen3-4B, cuantizado a Q8_0.

**Opcion A** — Descargar desde GitHub Releases (recomendado):
1. Ve a https://github.com/cjtemer-kaos/supernexus-v2/releases/tag/v2.1.0
2. Descarga las **3 partes** (`part1`, `part2`, `part3`) y el script de union:
   - Windows: `join_gguf.ps1`
   - Linux/Mac: `join_gguf.sh`
3. Coloca todos los archivos en `models/nexus-director-v6/`
4. Ejecuta:
   ```bash
   # Windows
   cd /ruta/supernexus-v2
   powershell -File models/nexus-director-v6/join_gguf.ps1

   # Linux/Mac
   cd /ruta/supernexus-v2
   chmod +x models/nexus-director-v6/join_gguf.sh
   ./models/nexus-director-v6/join_gguf.sh
   ```
5. Crea el modelo en Ollama:
   ```bash
   ollama create nexus-director-v6 -f models/nexus-director-v6/Modelfile
   ```

**Opcion B** — Transferir GGUF desde otra maquina (via USB/disco externo):
1. Copia el archivo `models/nexus-director-v6/nexus-director-v6-Q8_0.gguf` al directorio `models/nexus-director-v6/` en la maquina destino
2. Ejecuta:
   ```bash
   cd /ruta/supernexus-v2
   ollama create nexus-director-v6 -f models/nexus-director-v6/Modelfile
   ```

**Opcion C** — Usar qwen3:4b como base (pierde el fine-tuning, mantiene el system prompt):
   ```bash
   ollama pull qwen3:4b
   cd /ruta/supernexus-v2
   ollama create nexus-director-v6 -f models/Modelfile-director-v6
   ```

---

## 3. Instalar Dependencias Python

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

# MCP bridge necesita: fastmcp, httpx, aiohttp
pip install "fastmcp[cli]" httpx aiohttp
```

## 4. Configurar Entorno

```bash
cp .env.example .env
# Editar .env segun tu configuracion:
#   - OPENCODE_API_KEY (para modelos cloud gratuitos)
#   - BRAVE_API_KEY (para busqueda web)
```

## 5. Instalar opencode (OPCIONAL — para interfaz CLI agente)

```bash
# Windows (Powershell como Admin):
winget install OpenCode --source https://opencode.ai

# Linux/Mac:
curl -fsSL https://opencode.ai/install.sh | sh

# O usar el gestor de paquetes:
npm install -g opencode
```

### Configurar MCP tools

```bash
# Copiar config de opencode:
mkdir -p ~/.config/opencode
cp opencode.json.example ~/.config/opencode/opencode.json

# Editar paths en opencode.json segun tu instalacion
```

> **Ver seccion "MCP Tools Integradas" abajo para detalles de cada herramienta.**

---

## 6. Compilar la UI (Web)

La UI es una app React + Vite. Se compila una vez y queda servida automaticamente por el servidor.

```bash
cd ui

# Instalar dependencias (pnpm recomendado, npm funciona):
npm install

# Compilar para produccion:
npm run build

# Esto genera ui/dist/ con los archivos estaticos
cd ..
```

> Si ya tienes `ui/dist/` en el repo (incluido desde commit `83a2821`), puedes saltarte este paso.
> El servidor sirve `ui/dist/` automaticamente en `http://localhost:9400/`.

## 7. Iniciar el Servidor

```bash
# Iniciar API (puerto 9400):
python -m src.api.server 9400

# O usando el script:
.\start_servidor.bat
# (Linux: chmod +x start_servidor.sh && ./start_servidor.sh)
```

Abre `http://localhost:9400/` en tu navegador para ver la UI.

---

## 7. Servicios Docker (OPCIONAL)

```bash
docker compose up -d
```

Esto levanta:
- **Agent Zero** (`:50080`) — Sandbox Python para ejecucion segura de codigo
- **Redis** (`:6379`) — Cache distribuido
- **n8n** (`:5678`) — Automatizacion low-code

---

## 8. Verificar Instalacion

```bash
# Verificar modelos instalados:
ollama list

# Verificar que el API responde:
Invoke-RestMethod http://localhost:9400/health
# o
curl http://localhost:9400/health

# Verificar gemas (deberian responder todas):
python check_gems.py
```

---

## Arquitectura del Sistema

```
OpenCode (CLI/TUI)
   |
   |-- Provider: nexus/auto → SuperNEXUS API (port 9400)
   |      Brain: ${NEXUS_PROJECT_DIR}/brain/
   |
   |-- MCP Servers:
   |      nexus-bridge (38 tools via mcp_bridge_server.py)
   |      chrome-devtools (CDP browser automation)
   |      playwright (browser E2E)
   |      context7 (documentacion live)
   |      brave-search (web search)
   |      github (API GitHub)
   |      agent-browser (playwright Python)
   |
   |-- Ollama (local, port 11434)
   |      11 modelos
   |
   |-- Docker (opcional)
   |      Agent Zero (:50080)
   |      Redis (:6379)
   |      n8n (:5678)
```

---

## Enlaces

- Repo: `https://github.com/cjtemer-kaos/supernexus-v2`
- Documentacion opencode: `https://opencode.ai`
- Modelo Director v6: `nexus-director-v6:latest`
