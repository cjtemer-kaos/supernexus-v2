#!/bin/bash
# ==============================================================================
# NEXUS ECOLOGY - OPENCLAW FIX PERMISSIONS AND PATHS
# ==============================================================================
# Uso: export OPENCLAW_USER=youruser && sudo bash fix_openclaw.sh

OPENCLAW_USER="${OPENCLAW_USER:-$(whoami)}"
OPENCLAW_HOME="/home/${OPENCLAW_USER}"

echo "Fixing OpenClaw paths and permissions..."

# 1. Move from /root to user home if exists
if [ -d "/root/openclaw" ]; then
    echo "Moving /root/openclaw to ${OPENCLAW_HOME}/openclaw..."
    sudo mv /root/openclaw "${OPENCLAW_HOME}/"
fi

# 2. Fix ownership
echo "Setting ownership to ${OPENCLAW_USER}..."
sudo chown -R "${OPENCLAW_USER}:${OPENCLAW_USER}" "${OPENCLAW_HOME}/openclaw"

# 3. Restart service
echo "Restarting OpenClaw service..."
sudo systemctl restart openclaw

echo "Done. Service status:"
sudo systemctl status openclaw --no-pager
