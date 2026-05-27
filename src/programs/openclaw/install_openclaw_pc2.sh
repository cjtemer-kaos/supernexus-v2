#!/bin/bash
# ==============================================================================
# NEXUS ECOLOGY - OPENCLAW INSTALLATION SCRIPT
# Derived from Rinku's Tutorial: https://www.youtube.com/watch?v=nMOINXoii9E
# ==============================================================================
# Uso: export OLLAMA_URL=http://localhost:11434 && bash install_openclaw.sh

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
DEFAULT_MODEL="${DEFAULT_MODEL:-qwen2.5-coder:7b}"

echo "Starting OpenClaw Installation..."

# 1. Update and Prerequisites
echo "Updating system and installing dependencies..."
sudo apt update && sudo apt install -y curl git docker.io docker-compose

# 2. Install Node.js v24 (Official recommendation)
echo "Installing Node.js v24..."
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Verify Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 4. Clone OpenClaw
echo "Cloning OpenClaw repository..."
cd ~
git clone https://github.com/openclaw/openclaw.git
cd openclaw

# 5. Install PNPM (required for OpenClaw)
echo "Installing PNPM..."
sudo npm install -g pnpm

# 6. Build OpenClaw
echo "Building OpenClaw..."
pnpm install
pnpm build
pnpm ui:build

# 7. Setup Environment
echo "Configuring Nexus Integration..."
cat <<EOF > .env
# Brain Configuration
OLLAMA_BASE_URL="${OLLAMA_URL}"
DEFAULT_MODEL="${DEFAULT_MODEL}"

# UI Configuration
PORT=3000
EOF

# 8. Final Message
echo "=============================================================================="
echo "✅ OPENCLAW INSTALLED SUCCESSFULLY"
echo "=============================================================================="
echo "To start OpenClaw, run:"
echo "  pnpm start"
echo ""
echo "Then access the UI at: http://<PC2_IP>:3000"
echo "=============================================================================="
