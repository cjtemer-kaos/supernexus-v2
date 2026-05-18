# SuperNEXUS v2 - Requisitos y Dependencias

## Ya instalados (usuario los tiene)
- [x] **Ollama** - Motor de modelos locales
- [x] **Python 3.11+** - Runtime del backend
- [x] **Node.js 18+** - Runtime de la interfaz
- [x] **pnpm** - Package manager de Node

## Programas a instalar automaticamente

### Python (pip install -r requirements.txt)
- [ ] **aiohttp** >= 3.9.0 - Servidor HTTP async
- [ ] **httpx** >= 0.27.0 - Cliente HTTP async
- [ ] **requests** >= 2.31.0 - Cliente HTTP
- [ ] **ollama** >= 0.2.0 - Cliente Python de Ollama
- [ ] **pydantic** >= 2.5.0 - Validacion de datos
- [ ] **python-dotenv** >= 1.0.0 - Carga de .env
- [ ] **PyJWT** >= 2.8.0 - Autenticacion JWT
- [ ] **bcrypt** >= 4.1.0 - Hash de contrasenas
- [ ] **pytest** >= 7.4.0 - Testing
- [ ] **pytest-asyncio** >= 0.23.0 - Testing async

### Python - Vision (opcional)
- [ ] **mss** >= 9.0.0 - Capturas de pantalla
- [ ] **opencv-python** >= 4.9.0 - Procesamiento de imagenes
- [ ] **pytesseract** >= 0.3.10 - OCR (requiere Tesseract instalado en el sistema)
- [ ] **numpy** >= 1.26.0 - Calculo numerico

### Python - Audio (opcional)
- [ ] **edge-tts** >= 6.1.0 - Texto a voz (Windows)

### Node.js (pnpm install en ui/)
- [ ] **react** ^19.1.0 - Framework UI
- [ ] **react-dom** ^19.1.0 - Renderizado DOM
- [ ] **vite** ^7.0.4 - Build tool
- [ ] **typescript** ~5.9.0 - Tipado
- [ ] **tailwindcss** ^4.2.2 - Estilos
- [ ] **zustand** ^5.0.12 - Estado global
- [ ] **lucide-react** ^0.577.0 - Iconos
- [ ] **@tanstack/react-query** ^5.90.21 - Fetching de datos
- [ ] **react-markdown** ^10.1.0 - Renderizado Markdown
- [ ] **sonner** ^2.0.7 - Notificaciones toast

### Sistema operativo - Windows
- [ ] **Tesseract OCR** - Para vision/OCR (descargar de https://github.com/UB-Mannheim/tesseract/wiki)
  - Ruta por defecto: `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - Agregar al PATH o configurar TESSERACT_CMD en .env

### Modelos de Ollama (se descargan automaticamente)
- [ ] **qwen2.5:0.5b** - Chat rapido (default)
- [ ] **qwen2.5-coder:7b** - Programacion
- [ ] **deepseek-r1:8b** - Razonamiento
- [ ] **nemotron-3-nano:4b** - Chat ligero
- [ ] **qwen2.5vl:7b** - Vision (opcional, requiere GPU)

## Resumen de instalacion

### Paso 1: Dependencias Python
```powershell
pip install -r requirements.txt
```

### Paso 2: Dependencias Node
```powershell
cd ui
pnpm install
cd ..
```

### Paso 3: Tesseract OCR (opcional, para vision)
```powershell
# Descargar e instalar desde:
# https://github.com/UB-Mannheim/tesseract/wiki
# O con winget:
winget install --id UB-Mannheim.TesseractOCR
```

### Paso 4: Modelos de Ollama
```powershell
ollama pull qwen2.5:0.5b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:4b
# Opcional - vision:
ollama pull qwen2.5vl:7b
```

### Paso 5: Configurar .env
```powershell
copy .env.example .env
# Editar .env con tus configuraciones
```

### Paso 6: Iniciar
```powershell
scripts\start.bat
```

## Verificacion

```powershell
# Verificar Python
python --version

# Verificar Node
node --version

# Verificar Ollama
ollama list

# Verificar Tesseract (si instalaste)
tesseract --version

# Verificar dependencias Python
python -c "import aiohttp, httpx, pydantic, jwt; print('OK')"

# Verificar dependencias Node
cd ui && pnpm list --depth=0 && cd ..
```

## Espacio en disco requerido

| Componente | Espacio |
|------------|---------|
| Python + dependencias | ~500 MB |
| Node.js + dependencias | ~300 MB |
| Modelos Ollama (4 basicos) | ~8 GB |
| Modelo vision (opcional) | ~5 GB |
| **Total minimo** | **~9 GB** |
| **Total con vision** | **~14 GB** |

## RAM requerida

| Uso | RAM |
|-----|-----|
| Minimo (solo chat) | 4 GB |
| Recomendado (chat + codigo) | 8 GB |
| Con vision | 16 GB |
