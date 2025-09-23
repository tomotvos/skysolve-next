# Deploying SkySolve on a Raspberry Pi

This document describes the one-shot `scripts/deploy_pi.sh` script included in this repository and provides usage examples, tips, and warnings for deploying SkySolve on a dedicated Raspberry Pi.

## Overview

`deploy_pi.sh` performs the following steps:

- Creates a dedicated system user (default `skysolve`) if missing
- Deploys repository contents into `/opt/skysolve/current` by either:
  - Cloning from a provided `REPO_URL` (remote clone), or
  - Copying the current working checkout into the target (local copy)
- Creates a Python virtualenv at `/opt/skysolve/current/.venv` and installs the package with `pip install -e .`
- Creates `/opt/skysolve/logs` and ensures ownership
- Installs systemd unit files for the web and worker services (from `deploy/` if present, otherwise writes defaults)
- Enables and starts `skysolve-web.service` and `skysolve-worker.service`

## Usage modes

### 1) Local copy (recommended for development/testing)

This mode assumes you've already cloned the repository on the Pi into a safe path (e.g., `~/skysolve-next`) and want to copy that checkout into `/opt/skysolve/current`.

```bash
# On the Pi, clone once to your home directory (or use your existing checkout)
cd ~
git clone https://github.com/youruser/skysolve-next.git skysolve-next

# Run the deploy script from inside that checkout (as root)
cd skysolve-next
sudo ./scripts/deploy_pi.sh
```

What this does:
- Uses `rsync` to copy the working tree from your local checkout to `/opt/skysolve/current` (excludes `.venv`, `logs`, `__pycache__`)
- Creates virtualenv and installs the package
- Installs unit files and starts services

### 2) Remote clone (CI or clean deploy)

Let the Pi clone directly from your remote repository. Useful for unattended deploys or CI.

```bash
sudo REPO_URL=https://github.com/youruser/skysolve-next.git ./scripts/deploy_pi.sh
# Optionally specify branch
sudo REPO_URL=https://github.com/youruser/skysolve-next.git BRANCH=main ./scripts/deploy_pi.sh
```

This clones directly into `/opt/skysolve/current` as the `skysolve` service user.

## Important warnings and notes

- The script will remove `/opt/skysolve/current` before cloning/copying. Do NOT run the script from inside the eventual target directory unless you use `REPO_URL` instead.
- Avoid nested clones: do not clone the repo directly into `/opt/skysolve/current` prior to running the script unless you intend it to be the final target.
- If you want iterative updates after initial deployment, prefer:

```bash
cd /opt/skysolve/current
sudo -u skysolve git pull
sudo -u skysolve . .venv/bin/activate && pip install -e .
sudo systemctl restart skysolve-web skysolve-worker
```

- For production, the script uses a virtualenv at `/opt/skysolve/current/.venv`. This provides reproducible installs. If you prefer system-wide installs, run `sudo pip3 install .` but this is not recommended for maintainability.

- The script writes default systemd unit files (in `/etc/systemd/system/`) unless `deploy/skysolve-web.service` and `deploy/skysolve-worker.service` are present in the repo. Those `deploy/` unit files are copied if found.

## Verification and debugging

- Check service status:

```bash
sudo systemctl status skysolve-web
sudo systemctl status skysolve-worker
```

- Tail logs:

```bash
sudo journalctl -u skysolve-web -f
sudo journalctl -u skysolve-worker -f
# or if using the filesystem logs written by the unit files
tail -F /opt/skysolve/logs/*.log
```

- If ports are unreachable, verify firewall settings (iptables/ufw) and ensure services are listening on the expected ports (5001 web, 5002 LX200).

## Alternatives

- Docker: Containerize the app for immutable deployments.
- Use an external supervisor (e.g., Docker Compose, Kubernetes) for advanced setups.

## Optional improvements

- Add a `--no-restart` flag to the script to avoid automatically restarting services during an update.
- Add a confirmation prompt before deleting `/opt/skysolve/current`.
- Add an upgrade path for database migrations or config preservation.

---

If you want, I can also add a `--dry-run` mode to the script and implement any of the optional improvements above.
