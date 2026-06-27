#!/bin/bash
# ==============================================================================
# 🧠 NEXUS ECOLOGY - OPENCLAW + KALI TOOLS INSTALLATION FOR PC2 (REFINED)
# Target: Ubuntu 22.04 (Jammy)
# ==============================================================================

export DEBIAN_FRONTEND=noninteractive

set -e

echo "🚀 Starting Refined Implementation on PC2..."

# 1. Prerequisites (Node.js 24)
echo "🟢 Installing Node.js 24..."
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pnpm

# 2. Hacking Tools (Standard Repos - Safe)
echo "🛡️ Installing Standard Security Tools..."
sudo apt-get update
sudo apt-get install -y nmap sqlmap nikto gobuster hydra john hashcat git curl wget

# 3. Metasploit Framework (Official Installer - Safer than repo mix)
echo "🛡️ Installing Metasploit Framework (Official)..."
curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall
chmod 755 msfinstall
./msfinstall

# 4. Install OpenClaw
echo "📂 Cloning and Building OpenClaw..."
cd ~
if [ -d "openclaw" ]; then
    rm -rf openclaw
fi
git clone https://github.com/openclaw/openclaw.git
cd openclaw

pnpm install
pnpm build
pnpm ui:build

# 5. Configuration
echo "📝 Configuring OpenClaw..."
cat <<EOF > .env
OLLAMA_BASE_URL="http://localhost:11434"
DEFAULT_MODEL="qwen2.5-coder:7b"
PORT=3000
EOF

echo "=============================================================================="
echo "✅ IMPLEMENTATION COMPLETE ON PC2"
echo "=============================================================================="
echo "OpenClaw is ready. Tools installed: nmap, metasploit, sqlmap, etc."
echo "=============================================================================="
