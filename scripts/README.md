# SkySolve Setup & Deployment

Complete guide for setting up SkySolve in development and production environments.

## Development Setup

**`dev_setup.sh`** - Development environment (Mac/Linux/Pi)
- Creates `.venv` in current directory  
- Installs development dependencies
- Platform-aware (handles Pi-specific packages)
- Does NOT install system services

```bash
# Run from repository root
./scripts/dev_setup.sh

# Then activate and run
source .venv/bin/activate
uvicorn skysolve_next.web.app:app --reload --port 5001  # Web app
python -m skysolve_next.workers.solve_worker            # Solver
```

## Production Deployment

**`deploy_production.sh`** - Production deployment on Raspberry Pi
- Must run as root (sudo)
- Creates system user (`skysolve`) and installs to `/opt/skysolve`
- Sets up systemd services (`skysolve-web`, `skysolve-worker`)
- Creates `/opt/skysolve/logs` directory
- Supports both clean install and local deployment

### Clean Install (from GitHub)
```bash
sudo REPO_URL=https://github.com/youruser/skysolve-next.git ./scripts/deploy_production.sh
```

### Local Deployment (from repo directory)
```bash
# Clone/copy repo to Pi first
git clone https://github.com/youruser/skysolve-next.git
cd skysolve-next
sudo ./scripts/deploy_production.sh
```

### What the production script does:
1. Creates dedicated system user if missing
2. Deploys code to `/opt/skysolve/current` (clone from REPO_URL or copy from current directory)
3. Creates Python virtualenv and installs package with `pip install -e .`
4. Installs systemd unit files (from `deploy/` if present, otherwise writes defaults)
5. Enables and starts services

### Redeployment (Updates)

For updates to an existing production deployment:

**Method 1: Re-run deploy script (clean)**
```bash
# This will replace everything in /opt/skysolve/current
sudo REPO_URL=https://github.com/youruser/skysolve-next.git ./scripts/deploy_production.sh
```

**Method 2: Manual update (faster)**
```bash
# Pull latest code
cd /opt/skysolve/current
sudo -u skysolve git pull

# Update dependencies
sudo -u skysolve .venv/bin/pip install -e .

# Restart services
sudo systemctl restart skysolve-web skysolve-worker
```

**Method 3: Local code update**
```bash
# Copy your local changes to production and redeploy
sudo ./scripts/deploy_production.sh
```

## Verification & Debugging

**Check service status:**
```bash
sudo systemctl status skysolve-web skysolve-worker
```

**View logs:**
```bash
sudo journalctl -u skysolve-web -f
sudo journalctl -u skysolve-worker -f
# or filesystem logs
tail -F /opt/skysolve/logs/*.log
```

**Access services:**
- Web interface: `http://PI_IP_ADDRESS:5001`
- LX200 server: port `5002`

## Important Notes

### Safety Warnings
- Production script removes `/opt/skysolve/current` before deployment
- DO NOT run production script from `/opt/skysolve/current` unless using `REPO_URL`
- Script includes safety check to prevent copying directory to itself
- DO NOT delete `/opt/skysolve/logs` directory - services will fail to start without it

### Systemd Services
- `skysolve-web.service` - FastAPI web application
- `skysolve-worker.service` - Solve worker process
- Both run as `skysolve` user with automatic restart on failure

## Managing Multiple Versions

If you have legacy services installed and want to selectively start/stop versions:

```bash
# Install new version without auto-start at boot
sudo NO_AUTO_START=1 ./scripts/deploy_production.sh

# Services are installed but won't start automatically at boot
# Start manually when needed:
sudo systemctl start skysolve-web skysolve-worker

# Switch between versions:
sudo systemctl stop skysolve encodertoSkySafari                 # Stop legacy
sudo systemctl start skysolve-web skysolve-worker               # Start new

# Enable auto-start later if desired:
sudo systemctl enable skysolve-web skysolve-worker
```

### Options
- `NO_AUTO_START=1` - Install services but don't enable auto-start at boot
- `NO_RESTART=1` - Enable services but don't start them now
- `INSTALL_DIR=/custom/path` - Use custom installation directory  
- `SERVICE_USER=myuser` - Use custom service user
- `BRANCH=develop` - Deploy from specific git branch

**Option combinations:**
- Default: Enable auto-start + start now
- `NO_RESTART=1`: Enable auto-start but don't start now  
- `NO_AUTO_START=1`: Start now but don't enable auto-start
- `NO_AUTO_START=1 NO_RESTART=1`: Install only, don't enable or start

## Service Management

### Toggle Between Service Versions

Use `toggle_services.sh` to switch between legacy and next service versions:

```bash
# Switch to legacy services (skysolve, encodertoSkySafari)
./toggle_services.sh legacy

# Switch to next services (skysolve-web, skysolve-worker)  
./toggle_services.sh next
# or
./toggle_services.sh new

# Check status of all services
./toggle_services.sh status

# Show usage help
./toggle_services.sh
```

The script will:
- Stop the currently running services (if any)
- Start the requested service set
- Show the final status of all services
- Handle missing services gracefully

### Manual Service Management

If you prefer manual control:

```bash
# Stop everything
sudo systemctl stop skysolve-web skysolve-worker skysolve encodertoSkySafari

# Start next services
sudo systemctl start skysolve-web skysolve-worker

# Start legacy services  
sudo systemctl start skysolve encodertoSkySafari
```

## Key Differences

| Script | Purpose | Environment | Creates Services | Runs As |
|--------|---------|-------------|------------------|---------|
| `dev_setup.sh` | Development | Mac/Linux/Pi | No | Regular user |
| `deploy_production.sh` | Production | Pi only | Yes | Root (sudo) |
| `toggle_services.sh` | Service switching | Pi only | No | Root (sudo) |
