param(
    [switch]$NoUI,
    [int]$Port = 9000
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$env:PYTHONDONTWRITEBYTECODE = "1"
$env:NEXUS_BRAIN = "$ProjectDir\brain"
$env:PYTHONPATH = $ProjectDir

Write-Host "=== SuperNEXUS v2 ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectDir"
Write-Host "Brain: $env:NEXUS_BRAIN"
Write-Host "Port: $Port"
Write-Host ""

if (-not $NoUI) {
    $electronApp = "$ProjectDir\ui\node_modules\.bin\electron.cmd"
    $uiDist = "$ProjectDir\ui\dist\main\main.js"

    if (Test-Path $uiDist) {
        Write-Host "Starting Electron app..." -ForegroundColor Yellow
        Start-Process -NoNewWindow -FilePath $electronApp -ArgumentList $uiDist
    } else {
        Write-Host "Electron build not found. Starting server only." -ForegroundColor Yellow
        Write-Host "To build the desktop app: cd ui && pnpm install && pnpm run dist:win" -ForegroundColor DarkGray
        python "$ProjectDir\src\api\server.py" $Port
    }
} else {
    python "$ProjectDir\src\api\server.py" $Port
}
