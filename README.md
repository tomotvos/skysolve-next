# Skysolve Next

- **Web UI/API:** port **5001**
- **SkySafari parity:** read-only **LX200 server** on **5002** (RA/Dec only; no slews)
- **OnStep client (optional):** push solves via `:Sr/:Sd/:CM#` on port 9998
- **Dual solver support:** Astrometry.net (default) + Tetra3/Cedar (fast option)
- **Hotspot managed separately** via NetworkManager + GPIO7
- **mDNS (Avahi):** `_http._tcp` (5001), `_lx200._tcp` (5002)

## Quick start (dev, no camera)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
uvicorn skysolve_next.web.app:app --host 0.0.0.0 --port 5001 --reload
```
Run the worker (publishes to SkySafari + optionally to OnStep):
```bash
python -m skysolve_next.workers.solve_worker
```

## Systemd
See `services/*.service`. Adjust paths if installing under `/opt/skysolve-next`.
