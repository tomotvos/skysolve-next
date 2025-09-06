#!/usr/bin/env bash
set -euo pipefail

# Check for libcap-dev and libjpeg-dev and install if missing (Debian/Ubuntu/Raspberry Pi OS)
missing_pkgs=()
for pkg in libcap-dev libjpeg-dev; do
	if ! dpkg -s "$pkg" >/dev/null 2>&1; then
		missing_pkgs+=("$pkg")
	fi
done
if [ ${#missing_pkgs[@]} -ne 0 ]; then
	if [ "$EUID" -ne 0 ]; then
		echo "The following packages are required: ${missing_pkgs[*]}"
		echo "Please run the following command as root or with sudo, then re-run this script:"
		echo "  sudo apt-get update && sudo apt-get install -y ${missing_pkgs[*]}"
		exit 1
	else
		apt-get update && apt-get install -y "${missing_pkgs[@]}"
	fi
fi


# Ensure system package for libcamera Python bindings is installed
if ! dpkg -s python3-libcamera >/dev/null 2>&1; then
	if [ "$EUID" -ne 0 ]; then
		echo "python3-libcamera is required. Please run the following command as root or with sudo, then re-run this script:"
		echo "  sudo apt-get update && sudo apt-get install -y python3-libcamera"
		exit 1
	else
		apt-get update && apt-get install -y python3-libcamera
	fi
fi

# Create a Python virtual environment in the project directory with system site packages
python3 -m venv .venv --system-site-packages


# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip


# Install all dependencies in editable mode (including dev dependencies if specified)
pip install -e .[dev]

# Ensure picamera2 is installed (required for camera support)
pip install --upgrade picamera2

# Print instructions for running the app locally
echo "\nSetup complete!"
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo "To run the web app (FastAPI):"
echo "  uvicorn skysolve_next.web.app:app --reload"
echo "To run the solve worker:"
echo "  python skysolve_next/workers/solve_worker.py"
echo "\nNote: If you get a 'command not found' error for uvicorn, try running:"
echo "  pip install uvicorn[standard]"
