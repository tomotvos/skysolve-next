#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="/opt/skysolve-next"
sudo useradd -r -s /usr/sbin/nologin skysolve || true
sudo mkdir -p "$APP_ROOT"
sudo cp -r . "$APP_ROOT/"
cd "$APP_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
sudo cp services/skysolve-next.service /etc/systemd/system/
sudo cp services/skysolve-next-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now skysolve-next skysolve-next-web
