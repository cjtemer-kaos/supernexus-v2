# SuperNEXUS v2.0 - Silent Startup Script
# Inicia backend y UI sin ventanas visibles

$ErrorActionPreference = "SilentlyContinue"

# Matar procesos existentes
Get-Process | Where-Object {$_.ProcessName -in @("electron","node")} | Stop-Process -Force 2>$null
Start-Sleep 2

# Compilar preload y main
Set-Location '${NEXUS_PROJECT_DIR}\ui'
npm run build:preload 2>$null
npm run build:main 2>$null

# Iniciar Vite en segundo plano
$ViteArgs = "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Set-Location '${NEXUS_PROJECT_DIR}\ui'; npm run dev:renderer"
Start-Process powershell -ArgumentList $ViteArgs -WindowStyle Hidden

Write-Host "Iniciando Vite..." -ForegroundColor Yellow
Start-Sleep 5

# Verificar que Vite está corriendo
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 3
    if ($response.StatusCode -eq 200) {
        Write-Host "Vite iniciado correctamente" -ForegroundColor Green
    }
} catch {
    Write-Host "Error iniciando Vite" -ForegroundColor Red
}

# Iniciar Electron en segundo plano (usa dist/main/main.js compilado)
$ElectronArgs = "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Set-Location '${NEXUS_PROJECT_DIR}\ui'; node node_modules\electron\cli.js ."
Start-Process powershell -ArgumentList $ElectronArgs -WindowStyle Hidden

Write-Host "Electron iniciado" -ForegroundColor Green
Write-Host "UI disponible en http://localhost:5173" -ForegroundColor Cyan
