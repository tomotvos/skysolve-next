# Skysolve Next

## Overview

SkySolve Next is a modernized, open-source plate solving and telescope integration system designed for seamless use with SkySafari and OnStep controllers. The project aims to achieve feature parity with the legacy SkySolve, providing:

- A web-based UI and API for image solving, status monitoring, and configuration.
- A read-only LX200 server for SkySafari display (RA/Dec reporting, no telescope motion).
- Optional OnStep client integration to sync solved coordinates to the mount controller.
- Demo mode for hardware-free testing and development.
- Support for multiple solver backends (Astrometry.net, Tetra3/Cedar).
- Clean Python packaging, FastAPI, systemd units, mDNS/Avahi service discovery, and Pi-friendly deployment.

### Project Goals
- **Feature parity with legacy SkySolve** for SkySafari display and pointing.
- **Modern, maintainable architecture** using FastAPI, typed Python, and systemd.
- **Optional OnStep sync** for direct mount integration.
- **Demo mode** for quick verification and development without hardware.

---

## Credits & Legacy

SkySolve Next is inspired by and builds upon the pioneering work of the [original SkySolve project](https://github.com/githubdoe/skysolve). Special thanks and gratitude to the creators and contributors of legacy SkySolve, whose vision and implementation made modern plate solving and SkySafari integration possible for the amateur astronomy community. This project would not exist without their foundation and generosity in sharing their work.

---

## Technical Details

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
