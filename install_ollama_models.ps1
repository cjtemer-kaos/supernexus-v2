param(
    [switch]$NoDirector,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RELEASE_URL = "https://github.com/cjtemer-kaos/supernexus-v2/releases/download/v2.1.0"

Write-Host "=== SuperNEXUS v2 — Instalacion automatica (Windows) ===" -ForegroundColor Cyan

# --- Modelos regulares ---
$models = @(
    "carstenuhlig/omnicoder-2-9b:q4_k_m",
    "qwen3.5:9b",
    "deepseek-r1:8b",
    "qwen2.5-coder:7b",
    "qwen2.5vl:7b",
    "gemma4:12b",
    "nemotron-3-nano:4b",
    "qwen2.5:0.5b",
    "nomic-embed-text"
)

foreach ($model in $models) {
    Write-Host ">>> Descargando: $model" -ForegroundColor Yellow
    ollama pull $model
}

# --- Director v6 (desde GitHub Release) ---
if (-not $NoDirector) {
    Write-Host "`n=== Director v6: descargando desde GitHub Release ===" -ForegroundColor Cyan
    $ggufDir = "models/nexus-director-v6"
    New-Item -ItemType Directory -Path $ggufDir -Force | Out-Null
    $ggufPath = Join-Path $ggufDir "nexus-director-v6-Q8_0.gguf"

    if ((Test-Path $ggufPath) -and (-not $Force)) {
        Write-Host "✓ GGUF ya existe. Usa -Force para sobrescribir." -ForegroundColor Green
    } else {
        $parts = 1..3
        foreach ($i in $parts) {
            $partFile = Join-Path $ggufDir "nexus-director-v6-Q8_0.gguf.part$i"
            $partUrl = "$RELEASE_URL/nexus-director-v6-Q8_0.gguf.part$i"
            Write-Host "  Descargando parte $i/3..." -ForegroundColor Yellow
            curl.exe -L -o "$partFile" "$partUrl" 2>$null
            if (-not (Test-Path $partFile)) {
                Write-Host "Error: fallo descarga parte $i" -ForegroundColor Red
                exit 1
            }
            $smb = [Math]::Round((Get-Item $partFile).Length / 1MB, 1)
            Write-Host "  Parte $i: $smb MB" -ForegroundColor Green
        }

        Write-Host "  Reconstruyendo GGUF..." -ForegroundColor Yellow
        Copy-Item (Join-Path $ggufDir "nexus-director-v6-Q8_0.gguf.part1") $ggufPath
        for ($i = 2; $i -le 3; $i++) {
            $data = [System.IO.File]::ReadAllBytes((Join-Path $ggufDir "nexus-director-v6-Q8_0.gguf.part$i"))
            $fs = [System.IO.File]::OpenWrite($ggufPath)
            $fs.Seek(0, [System.IO.SeekOrigin]::End) | Out-Null
            $fs.Write($data, 0, $data.Length)
            $fs.Close()
        }
        $gb = [Math]::Round((Get-Item $ggufPath).Length / 1GB, 2)
        Write-Host "  GGUF reconstruido: $gb GB" -ForegroundColor Green

        # Limpiar partes
        1..3 | ForEach-Object { Remove-Item (Join-Path $ggufDir "nexus-director-v6-Q8_0.gguf.part$_") -Force }
    }

    Write-Host "  Creando modelo Ollama..." -ForegroundColor Yellow
    ollama create nexus-director-v6 -f "$ggufDir/Modelfile"
    Write-Host "✓ Director v6 instalado" -ForegroundColor Green
}

Write-Host "`n=== Compilando UI ===" -ForegroundColor Cyan
if (Test-Path "ui\package.json") {
    Push-Location "ui"
    if (-not (Test-Path "node_modules")) {
        Write-Host "  Instalando dependencias UI..." -ForegroundColor Yellow
        npm install --silent 2>$null
    }
    if (-not (Test-Path "dist\index.html")) {
        Write-Host "  Compilando UI..." -ForegroundColor Yellow
        npm run build 2>$null
    }
    Pop-Location
    if (Test-Path "ui\dist\index.html") {
        Write-Host "  UI compilada: ui/dist/" -ForegroundColor Green
    } else {
        Write-Host "  UI: compilation skipped (build manually with: cd ui && npm run build)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ui/package.json not found — UI pre-built in ui/dist/" -ForegroundColor Yellow
}

Write-Host "`n=== VERIFICACION ===" -ForegroundColor Cyan
ollama list

Write-Host "`n=== Instalacion completa ===" -ForegroundColor Green
Write-Host "Inicia el servidor: .\start_servidor.bat" -ForegroundColor Cyan
Write-Host "Abre la UI: http://localhost:9400/" -ForegroundColor Cyan