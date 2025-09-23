#!/usr/bin/env bash
set -euo pipefail

# One-shot deploy script for a dedicated Raspberry Pi
# - Creates system user
# - Installs code into /opt/skysolve/current (clones or copies current folder)
# - Creates venv and pip installs the package
# - Installs systemd unit files and starts/enables services

INSTALL_DIR=${INSTALL_DIR:-/opt/skysolve}
SERVICE_USER=${SERVICE_USER:-skysolve}
REPO_URL=${REPO_URL:-}
BRANCH=${BRANCH:-main}
WORKDIR=${WORKDIR:-$PWD}

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)." >&2
  exit 1
fi

echo "Deploying SkySolve to $INSTALL_DIR as user $SERVICE_USER"

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

echo "Reloading systemd and enabling services"
systemctl daemon-reload
systemctl enable --now skysolve-web.service skysolve-worker.service

echo "Deployment complete — check service status with:"
echo "  sudo systemctl status skysolve-web skysolve-worker"
echo "Logs:"
echo "  sudo journalctl -u skysolve-web -f"
echo "  sudo journalctl -u skysolve-worker -f"

exit 0
