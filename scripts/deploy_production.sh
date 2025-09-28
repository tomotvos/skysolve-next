#!/usr/bin/env bash
set -euo pipefail

# Production deployment script for Raspberry Pi
# Supports two modes:
#   1. Clean install: sudo REPO_URL=https://github.com/user/repo.git ./deploy_production.sh
#   2. Local deploy: sudo ./deploy_production.sh (from repo directory)
# Creates system user, installs to /opt/skysolve, sets up systemd services

INSTALL_DIR=${INSTALL_DIR:-/opt/skysolve}
SERVICE_USER=${SERVICE_USER:-skysolve}
REPO_URL=${REPO_URL:-}
BRANCH=${BRANCH:-main}
WORKDIR=${WORKDIR:-$PWD}
NO_RESTART=${NO_RESTART:-}
NO_AUTO_START=${NO_AUTO_START:-}

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)." >&2
  exit 1
fi

# Safety check: refuse to copy from target directory to itself
if [ -z "$REPO_URL" ] && [ "$(realpath "$WORKDIR")" = "$(realpath "$INSTALL_DIR/current")" ]; then
  echo "Error: Cannot copy from $WORKDIR to $INSTALL_DIR/current (same directory)" >&2
  echo "Either run from a different directory or use REPO_URL for clean install" >&2
  exit 1
fi

echo "🚀 Deploying SkySolve to $INSTALL_DIR as user $SERVICE_USER"
if [ -n "$REPO_URL" ]; then
  echo "📦 Mode: Clean install from $REPO_URL"
else
  echo "📁 Mode: Local deploy from $WORKDIR"
fi

# Create service user if missing
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd -r -m -d "$INSTALL_DIR" -s /usr/sbin/nologin "$SERVICE_USER"
  echo "Created user $SERVICE_USER"
fi

# Prepare directories
mkdir -p "$INSTALL_DIR"
chown "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

CURRENT_DIR="$INSTALL_DIR/current"
if [ -n "$REPO_URL" ]; then
  echo "Cloning $REPO_URL (branch $BRANCH) into $CURRENT_DIR"
  rm -rf "$CURRENT_DIR"
  sudo -u "$SERVICE_USER" git clone --branch "$BRANCH" "$REPO_URL" "$CURRENT_DIR"
else
  echo "No REPO_URL provided; copying from $WORKDIR to $CURRENT_DIR"
  rm -rf "$CURRENT_DIR"
  mkdir -p "$CURRENT_DIR"
  rsync -a --exclude '.venv' --exclude 'logs' --exclude '__pycache__' "$WORKDIR/" "$CURRENT_DIR/"
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$CURRENT_DIR"
fi

# Create and populate venv
echo "Creating virtualenv and installing dependencies"
sudo -u "$SERVICE_USER" bash -lc "cd '$CURRENT_DIR' && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip setuptools wheel && pip install -e ."

# Create logs directory
mkdir -p "$INSTALL_DIR/logs"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR/logs"

# Install systemd unit files from repo deploy/ if present, otherwise write defaults
DEPLOY_DIR="$CURRENT_DIR/deploy"
if [ -d "$DEPLOY_DIR" ] && [ -f "$DEPLOY_DIR/skysolve-web.service" ] && [ -f "$DEPLOY_DIR/skysolve-worker.service" ]; then
  echo "Copying unit files from $DEPLOY_DIR to /etc/systemd/system/"
  cp "$DEPLOY_DIR/skysolve-web.service" /etc/systemd/system/
  cp "$DEPLOY_DIR/skysolve-worker.service" /etc/systemd/system/
else
  echo "Writing default unit files to /etc/systemd/system/"
  cat > /etc/systemd/system/skysolve-web.service <<'SERVICE'
[Unit]
Description=SkySolve Web App
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}/current
Environment=PYTHONUNBUFFERED=1
ExecStart=${INSTALL_DIR}/current/.venv/bin/uvicorn skysolve_next.web.app:app --host 0.0.0.0 --port 5001
Restart=on-failure
RestartSec=5
StandardOutput=append:${INSTALL_DIR}/logs/web.log
StandardError=append:${INSTALL_DIR}/logs/web.log

[Install]
WantedBy=multi-user.target
SERVICE

  cat > /etc/systemd/system/skysolve-worker.service <<'SERVICE'
[Unit]
Description=SkySolve Solve Worker
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}/current
Environment=PYTHONUNBUFFERED=1
ExecStart=${INSTALL_DIR}/current/.venv/bin/python -m skysolve_next.workers.solve_worker
Restart=on-failure
RestartSec=5
StandardOutput=append:${INSTALL_DIR}/logs/worker.log
StandardError=append:${INSTALL_DIR}/logs/worker.log

[Install]
WantedBy=multi-user.target
SERVICE
fi

echo "Reloading systemd and configuring services"
systemctl daemon-reload

if [ -n "$NO_AUTO_START" ]; then
  # Install services but don't enable auto-start at boot
  if [ -z "$NO_RESTART" ]; then
    # Start services now but don't enable auto-start
    systemctl start skysolve-web.service skysolve-worker.service
    echo "✅ Services started (manual start only, no auto-start at boot)"
  else
    echo "⚠️  Services installed but not enabled or started (NO_AUTO_START=1, NO_RESTART=1)"
  fi
elif [ -z "$NO_RESTART" ]; then
  # Normal mode: enable auto-start and start now
  systemctl enable --now skysolve-web.service skysolve-worker.service
  echo "✅ Services enabled for auto-start and started"
else
  # Enable auto-start but don't start now
  systemctl enable skysolve-web.service skysolve-worker.service
  echo "⚠️  Services enabled for auto-start but not started (NO_RESTART=1)"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Check status:     sudo systemctl status skysolve-web skysolve-worker"
echo "View logs:        sudo journalctl -u skysolve-web -f"
echo "                  sudo journalctl -u skysolve-worker -f"
echo "Web interface:    http://$(hostname -I | awk '{print $1}'):5001"
echo "LX200 server:     port 5002"
echo ""
if [ -n "$NO_AUTO_START" ]; then
  echo "Manual service control:"
  echo "  sudo systemctl start skysolve-web skysolve-worker    # Start services"
  echo "  sudo systemctl stop skysolve-web skysolve-worker     # Stop services"
  echo "  sudo systemctl enable skysolve-web skysolve-worker   # Enable auto-start"
else
  echo "Service control:"
  echo "  sudo systemctl restart skysolve-web skysolve-worker  # Restart services"
  echo "  sudo systemctl disable skysolve-web skysolve-worker  # Disable auto-start"
fi
echo ""
echo "For updates:"
echo "  cd $INSTALL_DIR/current"
echo "  sudo -u $SERVICE_USER git pull"
echo "  sudo -u $SERVICE_USER .venv/bin/pip install -e ."
echo "  sudo systemctl restart skysolve-web skysolve-worker"

exit 0
