# SuperNEXUS v2 - Setup en Otra PC

Lee este archivo completo antes de hacer nada. Sigue los pasos en orden.

## Requisitos previos
- Python 3.11+ instalado y en PATH
- Git instalado
- Node.js 18+ instalado (para UI)
- Ollama instalado (https://ollama.com)

## Paso 1: Verificar que el codigo ya esta clonado
```bash
# Si estas leyendo este archivo, el codigo ya esta.
# Verifica que existan estas carpetas:
ls src/
ls brain/
ls ui/
ls data/
```

## Paso 2: Crear entorno virtual e instalar dependencias
```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Paso 3: Instalar modelos de Ollama
```powershell
# Windows
.\install_ollama_models.ps1
```

```bash
# Linux/Mac
chmod +x install_ollama_models.sh
./install_ollama_models.sh
```

Si el script no funciona, instala manualmente:
```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull qwen2.5:0.5b
ollama pull nomic-embed-text
ollama pull qwen2.5vl:7b
ollama pull nemotron-3-nano:4b
ollama pull gemma4:12b
```

## Paso 4: Compilar UI (si hay carpeta ui/src)
```powershell
# Windows
cd ui
npm install
npm run build
cd ..
```

```bash
# Linux/Mac
cd ui
npm install
npm run build
cd ..
```

## Paso 5: Arrancar el servidor
```powershell
# Windows - Opcion A (doble click)
.\start_servidor.bat

# Windows - Opcion B (terminal)
$env:PYTHONDONTWRITEBYTECODE="1"
$env:NEXUS_BRAIN="$PWD\brain"
python start_server.py 9000
```

```bash
# Linux/Mac
chmod +x start_servidor.sh
./start_servidor.sh
```

## Paso 6: Verificar que funciona
```powershell
# Probar endpoints
Invoke-RestMethod http://localhost:9000/api/health
Invoke-RestMethod http://localhost:9000/api/status
Invoke-RestMethod http://localhost:9000/api/brain/stats
```

```bash
# Linux/Mac
curl http://localhost:9000/api/health
curl http://localhost:9000/api/status
curl http://localhost:9000/api/brain/stats
```

Abrar en navegador: `http://localhost:9000`

## Paso 7: Si hay errores
- "Module not found": ejecuta `pip install -r requirements.txt` de nuevo
- "Port already in use": cambia el puerto en start_server.py o mata el proceso anterior
- "Ollama not running": ejecuta `ollama serve` en otra terminal
- UI no carga: verifica que exista `ui/dist/index.html`

## Variables de entorno importantes
```
PYTHONDONTWRITEBYTECODE=1    # Previene archivos .pyc
NEXUS_BRAIN=<ruta>/brain     # Apunta a la carpeta brain
PYTHONPATH=<ruta>             # Raiz del proyecto
```

## Estructura del proyecto
```
supernexus-v2/
  src/           # Codigo Python del servidor
  ui/            # Frontend React (source + dist)
  brain/         # Base de conocimientos (395 items)
  data/          # Configs de gemas, sesiones, etc.
  memory/        # Datos de memoria
  models/        # Modelfiles de Ollama
  start_server.py    # Punto de entrada
  start_servidor.bat # Launcher Windows
  start_servidor.sh  # Launcher Linux
  requirements.txt   # Dependencias Python
  install_ollama_models.ps1  # Instalador modelos Windows
  install_ollama_models.sh   # Instalador modelos Linux
```

## Puertos
- **9000**: Servidor principal (API + UI)
- **11434**: Ollama
- **50080**: Agent Zero (opcional, Docker)
