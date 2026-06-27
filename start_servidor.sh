#!/bin/bash
# SuperNEXUS v2 — Inicio del servidor
# Uso: chmod +x start_servidor.sh && ./start_servidor.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export NEXUS_BRAIN="${PROJECT_DIR}/brain"
export PYTHONPATH="${PROJECT_DIR}"

echo "=== SuperNEXUS v2 ==="
echo "Project: ${PROJECT_DIR}"
echo "Brain: ${NEXUS_BRAIN}"
echo "Port: 9400"
echo ""

cd "${PROJECT_DIR}"
python -m src.api.server 9400
