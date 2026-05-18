# SuperNEXUS v2

> Tu asistente de IA local - Centro de control personal inteligente

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

## Que es SuperNEXUS?

SuperNEXUS es un asistente de IA que funciona completamente en tu computadora local.
No envia tus datos a ningun servidor externo. Es tu centro de control personal para:

- **Programacion** - Escribir, revisar y refactorizar codigo
- **Investigacion** - Buscar y sintetizar informacion tecnica
- **Analisis de datos** - Procesar datos y generar reportes
- **Gestion de proyectos** - Organizar tareas y seguimiento
- **Automatizacion** - Control de PC, scripts, tareas repetitivas
- **Vision** - Analisis de imagenes y screenshots con IA
- **Memoria** - Aprende de tus interacciones y recuerda contexto

## Instalacion

### Windows

```powershell
# 1. Clonar o descargar el repositorio
git clone https://github.com/TU_USUARIO/supernexus-v2.git
cd supernexus-v2

# 2. Ejecutar el instalador
.\scripts\install.bat

# 3. Configurar
copy .env.example .env
# Editar .env con tu configuracion

# 4. Iniciar
.\scripts\start.bat
```

### Linux

```bash
# 1. Clonar
git clone https://github.com/TU_USUARIO/supernexus-v2.git
cd supernexus-v2

# 2. Instalar
chmod +x scripts/install.sh
./scripts/install.sh

# 3. Configurar
cp .env.example .env
# Editar .env

# 4. Iniciar
./scripts/start.sh
```

### Migrar desde v1

```powershell
# Windows
.\scripts\migrate_v1_to_v2.bat

# Linux
./scripts/migrate_v1_to_v2.sh
```

## Requisitos

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| RAM | 4 GB | 16 GB |
| Disco | 10 GB | 20 GB |
| CPU | 4 cores | 8 cores |
| GPU | - | NVIDIA con CUDA (opcional) |

**Software necesario:**
- Python 3.11+
- Node.js 18+ con pnpm
- Ollama (para modelos de IA locales)

Ver [DEPENDENCIES.md](DEPENDENCIES.md) para la lista completa.

## Uso

### Chat

Abre http://localhost:3000 en tu navegador y empieza a chatear.

### API

SuperNEXUS expone una API REST en http://localhost:9001 compatible con OpenAI:

```bash
# Ejemplo con curl
curl http://localhost:9001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "supernexus/auto",
    "messages": [{"role": "user", "content": "Hola SuperNEXUS"}]
  }'
```

### Linea de comandos

```bash
python -m src.api.server
```

## Arquitectura

```
supernexus-v2/
├── src/
│   ├── api/           # Servidor API (aiohttp)
│   ├── core/          # DirectorNexus, gemas, herramientas
│   ├── integrations/  # Integraciones externas
│   ├── memory/        # Sistema de memoria
│   ├── security/      # Auth, guardrails
│   └── tools/         # Herramientas (vision, shell, etc.)
├── ui/                # Interfaz web (React + Vite)
├── scripts/           # Instalacion y utilidades
├── data/              # Configuracion y proyectos
└── tests/             # Tests
```

### Gemas

SuperNEXUS tiene 22 "gemas" especializadas que se activan automaticamente segun la tarea:

| Gema | Funcion | Modelo |
|------|---------|--------|
| Director | Planificacion y orquestacion | deepseek-r1:8b |
| Code | Programacion | qwen2.5-coder:7b |
| Scholar | Investigacion web | deepseek-r1:8b |
| Architect | Diseno de sistemas | qwen2.5-coder:7b |
| Vision | Analisis de imagenes | qwen2.5vl:7b |
| Sage | Memoria y aprendizaje | deepseek-r1:8b |
| ... y 16 mas | | |

## Configuracion

### .env

```env
# Puerto del API
NEXUS_API_PORT=9001

# Ollama
OLLAMA_URL=http://localhost:11434

# API Keys (opcionales, para modelos cloud)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Modelos de Ollama

```bash
# Basicos (recomendados)
ollama pull qwen2.5:0.5b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:4b

# Opcional - vision
ollama pull qwen2.5vl:7b
```

## Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install -r requirements.txt
cd ui && pnpm install && cd ..

# Ejecutar tests
pytest tests/ -v

# Ejecutar en modo desarrollo
python -m src.api.server
cd ui && pnpm dev
```

## Releases

Las distribuciones pre-construidas estan disponibles en [GitHub Releases](../../releases).

### Construir desde fuente

```bash
python scripts/build_distro.py --platform windows --version 2.0.0
python scripts/build_distro.py --platform linux --version 2.0.0
```

## Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

## Contribuir

1. Fork el repositorio
2. Crea tu rama de feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request
