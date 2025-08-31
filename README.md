# Skysolve Next

- **Web UI/API:** port **5001**
- **OnStep sync-first:** Skysolve plate-solves and **syncs coordinates to OnStep**. SkySafari connects to OnStep directly.
- **Dual solver support:** Astrometry.net (default) + Tetra3/Cedar (fast option)
- **Hotspot managed separately** via NetworkManager + GPIO7
- **mDNS (Avahi):** `_http._tcp` (5001)

## Quick start (dev, no camera)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
uvicorn skysolve_next.web.app:app --host 0.0.0.0 --port 5001 --reload
```

## Systemd
See `services/*.service`. Adjust paths if installing under `/opt/skysolve-next`.
