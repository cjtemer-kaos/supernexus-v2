#!/bin/bash
# nexus-wake.sh - Despierta agentes de la colmena via SSH
# Uso: ssh user@host "bash /path/to/nexus-wake.sh [agente]"
# Configurar: export NEXUS_HOME=/path/to/nexus-ia

AGENT=${1:-"all"}
NEXUS_DIR="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"

echo "=== NexusHive Wake Call ==="
echo "Agente: $AGENT"
echo "Hora: $(date)"

# Verificar si hay tareas pendientes
TASKS=$(sqlite3 "$NEXUS_DIR/memory/message_board.db" "SELECT COUNT(*) FROM messages WHERE target IN ('$AGENT', '*') AND msg_type='task' AND id > (SELECT COALESCE(MAX(id), 0) FROM messages WHERE sender='system' AND content LIKE 'ACK%');")

if [ "$TASKS" -gt 0 ]; then
    echo "Tareas pendientes: $TASKS"
    
    # Iniciar loop autonomo temporal
    cd "$NEXUS_DIR"
    python3 src/agents/nexus_autonomous_loop.py --agent "$AGENT" --once &
    echo "Agente $AGENT activado para procesar tareas"
else
    echo "Sin tareas pendientes para $AGENT"
fi

# Estado del sistema
echo ""
echo "Estado del sistema:"
echo "  Python: $(which python3)"
echo "  Ollama: $(curl -s http://localhost:11434/api/tags | python3 -c 'import sys,json; print(len(json.load(sys.stdin).get("models",[])))' 2>/dev/null || echo 'offline')"
echo "  DB: $(ls -la "$NEXUS_DIR/memory/message_board.db" 2>/dev/null | awk '{print $5, "bytes"}')"
