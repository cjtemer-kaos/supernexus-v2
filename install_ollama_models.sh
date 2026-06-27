#!/bin/bash
set -e

RELEASE_URL="https://github.com/cjtemer-kaos/supernexus-v2/releases/download/v2.1.0"

echo "=== SuperNEXUS v2 — Instalacion automatica (Linux/Mac) ==="

# --- Modelos regulares ---
MODELS=(
    "carstenuhlig/omnicoder-2-9b:q4_k_m"
    "qwen3.5:9b"
    "deepseek-r1:8b"
    "qwen2.5-coder:7b"
    "qwen2.5vl:7b"
    "gemma4:12b"
    "nemotron-3-nano:4b"
    "qwen2.5:0.5b"
    "nomic-embed-text"
)

for model in "${MODELS[@]}"; do
    echo ">>> Descargando: $model"
    ollama pull "$model"
done

# --- Director v6 (desde GitHub Release) ---
echo ""
echo "=== Director v6: descargando desde GitHub Release ==="

GGUF_DIR="models/nexus-director-v6"
GGUF_PATH="$GGUF_DIR/nexus-director-v6-Q8_0.gguf"
mkdir -p "$GGUF_DIR"

if [ -f "$GGUF_PATH" ] && [ "$1" != "--force" ]; then
    echo "✓ GGUF ya existe. Usa --force para sobrescribir."
else
    for i in 1 2 3; do
        PART="$GGUF_DIR/nexus-director-v6-Q8_0.gguf.part$i"
        echo "  Descargando parte $i/3..."
        curl -L -o "$PART" "$RELEASE_URL/nexus-director-v6-Q8_0.gguf.part$i"
        if [ ! -f "$PART" ]; then
            echo "Error: fallo descarga parte $i"
            exit 1
        fi
        echo "  Parte $i: $(du -h "$PART" | cut -f1)"
    done

    echo "  Reconstruyendo GGUF..."
    cp "$GGUF_DIR/nexus-director-v6-Q8_0.gguf.part1" "$GGUF_PATH"
    cat "$GGUF_DIR/nexus-director-v6-Q8_0.gguf.part2" >> "$GGUF_PATH"
    cat "$GGUF_DIR/nexus-director-v6-Q8_0.gguf.part3" >> "$GGUF_PATH"
    echo "  GGUF reconstruido: $(du -h "$GGUF_PATH" | cut -f1)"

    # Limpiar partes
    rm -f "$GGUF_DIR"/nexus-director-v6-Q8_0.gguf.part{1,2,3}
fi

echo "  Creando modelo Ollama..."
ollama create nexus-director-v6 -f "$GGUF_DIR/Modelfile"
echo "✓ Director v6 instalado"

echo ""
echo "=== Compilando UI ==="
if [ -f "ui/package.json" ]; then
    cd ui
    if [ ! -d "node_modules" ]; then
        echo "  Instalando dependencias UI..."
        npm install --silent 2>/dev/null || true
    fi
    if [ ! -f "dist/index.html" ]; then
        echo "  Compilando UI..."
        npm run build 2>/dev/null || true
    fi
    cd ..
    if [ -f "ui/dist/index.html" ]; then
        echo "  UI compilada: ui/dist/"
    else
        echo "  UI: compilation skipped (build manually with: cd ui && npm run build)"
    fi
else
    echo "  ui/package.json not found — UI pre-built in ui/dist/"
fi

echo ""
echo "=== VERIFICACION ==="
ollama list

echo ""
echo "=== Instalacion completa ==="
echo "Inicia el servidor: ./start_servidor.sh"
echo "Abre la UI: http://localhost:9400/"