@echo off
REM SuperNEXUS v2 — Desktop Launcher
REM Double-click this file to start SuperNEXUS as a normal desktop app
SETLOCAL
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0SuperNEXUS.ps1"
ENDLOCAL
