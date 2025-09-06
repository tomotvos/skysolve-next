#!/usr/bin/env bash
set -euo pipefail

# Create a Python virtual environment in the project directory
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies in editable mode (including dev dependencies if specified)
pip install -e .[dev]

# Print instructions for running the app locally
echo "\nSetup complete!"
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo "To run the web app:"
echo "  python skysolve_next/web/app.py"
echo "To run the solve worker:"
echo "  python skysolve_next/workers/solve_worker.py"
