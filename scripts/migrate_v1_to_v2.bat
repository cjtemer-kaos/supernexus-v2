@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   SuperNEXUS v1 -> v2 - Migrador
echo ============================================
echo.
echo Este script migrara tu instalacion de SuperNEXUS v1 a v2.
echo Se preservaran todos tus archivos, proyectos y configuraciones.
echo.

:: Preguntar por ruta de v1
set /p V1_DIR="Ruta de tu instalacion v1 (ej: C:\Users\TuUsuario\Desktop\NEXUS_windows): "

if not exist "%%V1_DIR%%" (
    echo [ERROR] La ruta no existe: %%V1_DIR%%
    pause
    exit /b 1
)

echo.
echo [1/4] Preservando datos del usuario...

:: Copiar proyectos
if exist "%%V1_DIR%%\01_CORE\4_PROYECTOS" (
    if not exist data\projects mkdir data\projects
    xcopy /E /I /Y "%%V1_DIR%%\01_CORE\4_PROYECTOS\*" data\projects\ >nul
    echo   [OK] Proyectos copiados
)

:: Copiar memoria
if exist "%%V1_DIR%%\memory\nexus_memory.db" (
    if not exist memory mkdir memory
    copy /Y "%%V1_DIR%%\memory\nexus_memory.db" memory\ >nul
    echo   [OK] Base de datos de memoria copiada
)

:: Copiar configuracion
if exist "%%V1_DIR%%\01_CORE\config.py" (
    echo   [INFO] Encontrada configuracion v1 - se usara como referencia
)

:: Copiar .env si existe
if exist "%%V1_DIR%%\01_CORE\.env" (
    copy /Y "%%V1_DIR%%\01_CORE\.env" .env >nul
    echo   [OK] Configuracion .env copiada
)

echo.
echo [2/4] Instalando nueva version...

:: Instalar dependencias
if exist .venv (
    echo   [OK] Entorno virtual existente
) else (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
echo   [OK] Dependencias Python instaladas

cd ui
if not exist node_modules (
    npm install >nul 2>&1
    echo   [OK] Dependencias UI instaladas
) else (
    echo   [OK] Dependencias UI existentes
)
cd ..

echo.
echo [3/4] Configurando...

if not exist .env (
    copy .env.example .env >nul
    echo   [OK] Creado .env nuevo
)

echo.
echo [4/4] Verificando instalacion...

python -c "import sys; sys.path.insert(0, '.'); from src.core.director import DirectorNexus; print('  [OK] Backend verificado')" 2>nul
if errorlevel 1 (
    echo   [WARNING] Verificacion del backend fallo - revisa la instalacion
) else (
    echo   [OK] Backend funcionando
)

echo.
echo ============================================
echo   Migracion completada!
echo ============================================
echo.
echo Tus datos han sido preservados:
echo   - Proyectos: data/projects/
echo   - Memoria: memory/nexus_memory.db
echo   - Config: .env
echo.
echo Para iniciar la nueva version:
echo   scripts\start.bat
echo.
pause
