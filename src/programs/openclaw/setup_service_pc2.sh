#!/bin/bash
# ==============================================================================
# NEXUS ECOLOGY - OPENCLAW SERVICE SETUP
# ==============================================================================
# Uso: export OPENCLAW_USER=youruser && export OPENCLAW_DIR=/path/to/openclaw && sudo bash setup_service.sh

OPENCLAW_USER="${OPENCLAW_USER:-$(whoami)}"
OPENCLAW_DIR="${OPENCLAW_DIR:-/opt/openclaw}"

echo "Creating OpenClaw systemd service..."

cat <<EOF | sudo tee /etc/systemd/system/openclaw.service
[Unit]
Description=OpenClaw AI Agent
After=network.target ollama.service

[Service]
Type=simple
User=${OPENCLAW_USER}
WorkingDirectory=${OPENCLAW_DIR}
Environment="CI=true"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/pnpm start
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable openclaw
sudo systemctl start openclaw

echo "✅ OpenClaw service is now ACTIVE on PC2."
sudo systemctl status openclaw --no-pager
