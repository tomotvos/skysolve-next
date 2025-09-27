#!/usr/bin/env bash
set -euo pipefail

# Development setup script for SkySolve (Mac/Linux/Pi)
# Creates .venv in current directory and installs development dependencies
# Does NOT install system services - use deploy_production.sh for that

echo "Setting up SkySolve development environment..."

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="mac"
elif [[ -f /etc/os-release ]] && grep -q "Raspberry Pi" /etc/os-release; then
    PLATFORM="pi"
elif [[ -f /etc/debian_version ]]; then
    PLATFORM="debian"
else
    PLATFORM="unknown"
    echo "Warning: Unknown platform, proceeding with basic setup"
fi

# Install system dependencies on Raspberry Pi/Debian
if [[ "$PLATFORM" == "pi" || "$PLATFORM" == "debian" ]]; then
    missing_pkgs=()
    for pkg in libcap-dev libjpeg-dev python3-dev python3-venv; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing_pkgs+=("$pkg")
        fi
    done
    
    # Add Pi-specific packages
    if [[ "$PLATFORM" == "pi" ]]; then
        if ! dpkg -s python3-libcamera >/dev/null 2>&1; then
            missing_pkgs+=("python3-libcamera")
        fi
    fi
    
    if [ ${#missing_pkgs[@]} -ne 0 ]; then
        if [ "$EUID" -ne 0 ]; then
            echo "The following system packages are required: ${missing_pkgs[*]}"
            echo "Please run: sudo apt-get update && sudo apt-get install -y ${missing_pkgs[*]}"
            echo "Then re-run this script."
            exit 1
        else
            echo "Installing required system packages..."
            apt-get update && apt-get install -y "${missing_pkgs[@]}"
        fi
    fi
fi

# Create virtual environment
echo "Creating Python virtual environment..."
if [[ "$PLATFORM" == "pi" ]]; then
    # Use system site packages on Pi for libcamera access
    python3 -m venv .venv --system-site-packages
else
    python3 -m venv .venv
fi

# Activate and upgrade pip
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install package in development mode
echo "Installing SkySolve package and dependencies..."
pip install -e .[dev]

# Install Pi-specific packages
if [[ "$PLATFORM" == "pi" ]]; then
    pip install --upgrade picamera2
fi

echo ""
echo "✅ Development setup complete!"
echo ""
echo "Usage:"
echo "  source .venv/bin/activate        # Activate environment"
echo "  uvicorn skysolve_next.web.app:app --reload --port 5001  # Run web app"
echo "  python -m skysolve_next.workers.solve_worker            # Run solver"
echo ""
if [[ "$PLATFORM" == "pi" ]]; then
    echo "For production deployment with systemd services, use:"
    echo "  sudo ./scripts/deploy_production.sh"
fi
