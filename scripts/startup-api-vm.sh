#!/usr/bin/env bash
# GCP startup script for API VMs.
# Paste the content of this file into:
#   GCP Console → Instance Template → Management → Startup script
#
# Or pass it via gcloud:
#   --metadata-from-file startup-script=scripts/startup-api-vm.sh
#
# IMPORTANT: set DATA_VM_IP to your data VM's internal IP before creating
# the instance template.
set -euo pipefail

DATA_VM_IP="10.128.0.2"
REPO="https://github.com/Som401/retail-stream-fastapi.git"
PROJECT_DIR="/opt/retail-stream-fastapi"

# ── Install Docker if not present ───────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin git
  systemctl enable docker
  systemctl start docker
fi

# ── Install docker-compose standalone (for older Debian) ────────────────────
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
  curl -SL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

# ── Kernel tuning for high connections ──────────────────────────────────────
cat > /etc/sysctl.d/99-loadtest.conf <<'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.tcp_tw_reuse = 1
EOF
sysctl --system

# ── Clone or update the repo ─────────────────────────────────────────────────
if [ -d "$PROJECT_DIR/.git" ]; then
  git -C "$PROJECT_DIR" fetch origin main
  git -C "$PROJECT_DIR" reset --hard origin/main
else
  git clone "$REPO" "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# ── Start the API stack ──────────────────────────────────────────────────────
export DATA_VM_IP="$DATA_VM_IP"

if docker compose version &>/dev/null 2>&1; then
  docker compose -f docker-compose.api.yaml up -d --build
else
  docker-compose -f docker-compose.api.yaml up -d --build
fi

echo "API VM startup complete. DATA_VM_IP=$DATA_VM_IP"
