@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   SuperNEXUS v2.0 - Instalador Windows
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.11+ desde https://python.org
    pause
    exit /b 1
)
echo [OK] Python instalado

:: Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no encontrado. Instala Node.js 18+ desde https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js instalado

:: Verificar Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama no encontrado. Para modelos locales, instala desde https://ollama.ai
    echo.
    set /p CONTINUE="Continuar sin Ollama? (s/n): "
    if /i not "%%CONTINUE%%"=="s" exit /b 1
) else (
    echo [OK] Ollama instalado
)

:: Verificar Tesseract (opcional, para vision)
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Tesseract OCR no encontrado. La funcion de vision no estara disponible.
    echo         Para instalar: winget install --id UB-Mannheim.TesseractOCR
) else (
    echo [OK] Tesseract OCR instalado
)

:: Crear entorno virtual
echo.
echo [1/5] Creando entorno virtual...
python -m venv .venv
call .venv\Scripts\activate.bat

:: Instalar dependencias Python
echo [2/5] Instalando dependencias Python...
pip install -r requirements.txt

:: Instalar dependencias Node
echo [3/5] Instalando dependencias de la interfaz...
cd ui
if not exist node_modules (
    if exist pnpm-lock.yaml (
        npx pnpm install
    ) else if exist package-lock.json (
        npm install
    ) else (
        npm install
    )
)
cd ..

:: Configurar entorno
echo [4/5] Configurando entorno...
if not exist .env (
    copy .env.example .env
    echo [INFO] Creado .env - Editalo con tu configuracion
)

:: Descargar modelos recomendados
echo [5/5] Verificando modelos de Ollama...
ollama list | findstr "qwen2.5:0.5b" >nul
if errorlevel 1 (
    echo Descargando modelo qwen2.5:0.5b...
    ollama pull qwen2.5:0.5b
) else (
    echo [OK] Modelo qwen2.5:0.5b ya instalado
)

echo.
echo ============================================
echo   Instalacion completada!
echo ============================================
echo.
echo Para iniciar SuperNEXUS:
echo   scripts\start.bat
echo.
echo O manualmente:
echo   python -m src.api.server
echo.
echo Para ver todos los requisitos: DEPENDENCIES.md
echo.
pause
