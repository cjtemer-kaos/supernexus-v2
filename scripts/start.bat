@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   SuperNEXUS v2.0 - Iniciando...
echo ============================================
echo.

:: Activar entorno virtual
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: Establecer encoding
set PYTHONIOENCODING=utf-8

:: Iniciar backend
echo Iniciando backend API en puerto 9001...
start "SuperNEXUS Backend" python -m src.api.server

:: Esperar un momento
timeout /t 3 /nobreak >nul

:: Iniciar interfaz web
echo Iniciando interfaz web...
cd ui
start "SuperNEXUS UI" npx vite --open
cd ..

echo.
echo SuperNEXUS iniciado!
echo   Backend: http://localhost:9001
echo   UI:      http://localhost:5173
echo.
echo Presiona Ctrl+C en cada ventana para detener.
echo.
pause
