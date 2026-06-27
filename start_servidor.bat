@echo off
REM SuperNEXUS v2 — Inicio del servidor (Windows)
SETLOCAL

SET PROJECT_DIR=%~dp0
SET PYTHONDONTWRITEBYTECODE=1
SET NEXUS_BRAIN=%PROJECT_DIR%brain
SET PYTHONPATH=%PROJECT_DIR%

echo === SuperNEXUS v2 ===
echo Project: %PROJECT_DIR%
echo Brain: %NEXUS_BRAIN%
echo Port: 9400
echo.

cd /d "%PROJECT_DIR%"
python -m src.api.server 9400

ENDLOCAL
