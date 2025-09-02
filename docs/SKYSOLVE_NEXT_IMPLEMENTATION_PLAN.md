# SkySolve Next — Updated Implementation Plan

**Purpose:** actionable implementation plan prioritizing SkySolve parity (image solving + SkySafari integration) and preparing for OnStep integration. This file is intended to be added to the repository `docs/` folder and used by agents or humans working in VS Code (agent mode).

> Notes / context
> - Current state: demo web UI present, LX200 handler implemented and tested locally, Astrometry.net installed by the project's installation script and used as default solver. LX200 tracking to SkySafari has been verified locally after firewall adjustments. Some dependency compatibility issues appeared on Python 3.13 (package version constraints). The project should target a stable Python for Raspberry Pi (recommend Python **3.11**).

---

## High-level goals (must-haves)
1. **Parity with existing SkySolve feature set**
   - Image solving (demo images → solved RA/Dec).
   - SkySafari support: provide LX200-compatible endpoint so SkySafari can track/display where SkySolve is pointing (readonly position reporting). Default SkySafari port: **5002**.
   - Web UI with daytime / night (red-muted) mode, default web UI port: **5001**.
2. **Two solver support** (selectable at runtime)
   - **Astrometry.net** (already supported by current install). Keep as fallback / baseline.
   - **Tetra (Tetra3)** — integrate the fastest, recommended Tetra implementation for quick solves.
3. **OnStep integration (client)**
   - Push solved RA/Dec to OnStep to update mount calibration. OnStep remains the authoritative mount controller; SkySolve only provides calibration data.
4. **Robust packaging & runtime on Raspberry Pi**
   - Target Python **3.11** for Pi compatibility with solver libraries / binary wheels.
   - Provide a reproducible venv (use `venv --copies`) and a simple `run_skysolve.sh` runner script.
5. **Operational and security concerns**
   - Default ports: Web UI `5001`, SkySafari/LX200 `5002`, API/control port `5001` (same as web UI), SkySafari tracking port `5002` (so side-by-side SkySolve instances won't clash). Ensure clear docs if user runs multiple instances.
   - Document PF / macOS firewall guidance (session-based PF anchor for testing and instructions for persistent config on macOS / iptables on Linux).

---

## Scope: must-have vs stretch goals
### Must-have (for initial release)
- Image solve flow for demo image(s) → RA/Dec using Astrometry.net.
- Bindable solver interface so Tetra can be added (adapter pattern).
- LX200 server that returns current solved RA/Dec and can be polled by SkySafari on `5002` (readonly subset of protocol).
- Web UI: status page, solver selection dropdown, day/night toggle with red theme for night mode.
- OnStep client: socket-based client that can push solves to OnStep (configurable host/port).
- Packaging: install script for Linux/Raspbian that prepares venv, installs Python deps (pyproject/requirements), and verifies Astrometry working.
- Unit tests for solver adapter and LX200 server logic, basic integration test harness for solve→OnStep push (mocking OnStep in CI).

### Stretch / later
- Full Tetra integration (if C/compiled required, produce cross-compiled binaries or Docker build pipeline).
- Auto-hotspot: implement as separate service vs built-in (see Open Questions below).
- Image pre-processing pipeline (debayer, star detection, quality filters).
- Launchd / systemd service definitions for automatic startup on macOS/Linux/RPi.
- User account / API-key based access for remote control via web UI.
- CI cross-build artifacts for Pi (optional).

---

## Architecture & components (summary)
- `skysolve_next/`
  - `solvers/` — solver adapter interface + implementations (`astrometry_adapter.py`, `tetra_adapter.py`)
  - `workers/` — solve worker(s) that accept images, invoke solver adapters, and emit results
  - `publish/` — LX200 server implementation (listening on `0.0.0.0:5002`), SkySafari handler (readonly commands only)
  - `onstep/` — OnStep client code and config (push solves to OnStep; includes unit tests)
  - `web/` — FastAPI/Flask app (web UI), with day/night theme and endpoints for status and control (runs on `0.0.0.0:5001`)
  - `config/` — default YAML/JSON config + sample env file `.env.sample`
  - `scripts/` — helper scripts: `run_skysolve.sh`, `install_pi.sh`, `allow_firewall_explicit.sh` (examples)
  - `docs/` — PRD, Implementation Plan, and supporting docs (place this file here).

---

## Ports & Defaults (explicit)
- Web UI & API (control/command): **5001** (HTTP, prefer HTTPS in production)
- SkySafari / LX200 server (readonly position): **5002** (TCP, LX200-like plain text protocol)
- Optional diagnostic / API socket: **5003** (reserve for alternative protocol if needed)
> Note: Reconfigure files and `README` must mention these explicit port defaults and how to override via environment variables or config file.

---

## Solver integration plan (Astrometry.net + Tetra)
1. **Adapter interface** (`SolverAdapter` minimal API):
   - `solve(image_path) -> SolveResult` (RA, Dec, error, confidence, solve_time_ms)
   - `status()` (version, available, config)
2. **Astrometry adapter (existing)**:
   - Wrap CLI invocation (or use the local Astrometry Python bindings if installed).
   - Ensure working directory, index files path, and timeouts are configurable.
   - Provide a wrapper that retries and returns structured results.
3. **Tetra adapter**:
   - Identify an implementable Tetra3 binary or Python binding. Options:
     - Embed existing C binary (preferred for speed) and call via `subprocess` with safe args. Provide build instructions if compilation required on Pi.
     - Use a Docker image on dev/CI to build a static binary for RPi (cross-compile) and embed artifact in `third_party/` or publish build artifacts in releases.
   - Implement `tetra_adapter.py` that conforms to `SolverAdapter` and includes fallback to Astrometry on failure.
4. **Configuration**:
   - Expose solver selection in web UI and via `SKYSOLVE_SOLVER` env var / config file.
   - Default solver: `astrometry` (until Tetra integration is validated and installed).

---

## OnStep integration (design)
- **Role:** SkySolve acts as an OnStep *client* that pushes solved RA/Dec and optionally plate-solve metadata (timestamp, error, confidence) to OnStep so OnStep can update mount calibration/pointing model.
- **Interface:** OnStep accepts commands over TCP (OnStep protocol) — implement a minimal client to send the appropriate SET or CAL commands. Provide a config section with `ONSTEP_HOST`, `ONSTEP_PORT`, `ONSTEP_ENABLED`.
- **Flow:** After a successful solve, worker calls `OnStepClient.push_solve(solver_result)`. Retries and backoff on connect failure. Log per-push outcome.
- **Testing:** Provide a mock OnStep server for CI that verifies correct commands were issued.

References: OnStep docs — see `docs/references` at repository root.

---

## SkySafari / LX200 behavior
- Implement LX200 commands needed for SkySafari readonly operations (e.g., `:GR#` RA, `:GD#` Dec, `:RS#` slew status etc.), and **avoid** implementing move/go commands that would let SkySolve control the mount. The mount control should be via OnStep (user may configure SkySafari to talk to OnStep directly).
- Security: do not allow any command that moves the mount from this LX200 server; document that it is read-only and meant only for display.

---

## Web UI & UX details
- Tech: FastAPI + simple React/vanilla front-end (or Flask + small JS). Keep server-side minimal to run on Pi.
- Night mode: CSS variables and a toggle in UI; default themes: `day` (light) and `night` (muted red palette). Provide accessible color contrast for night mode (low-blue output).
- Pages:
  - Dashboard / Status (solver status, last solution, OnStep status)
  - Image upload / solve trigger (demo image)
  - Settings (solver selection, OnStep config, ports, advanced)
  - Logs / debug tail (debug-only)
- API endpoints should be documented in `docs/api.md` with examples (curl).

---

## Packaging & Pi runtime guidance
- Target Python: **3.11** for Raspberry Pi compatibility with third-party solver libs. Document in README and in the `install_pi.sh` script.
- Create `install_pi.sh` that:
  - Installs system deps for Astrometry/Tetra (index files, libjpeg-dev, build-essentials), and required packages for the wheel building (if needed).
  - Creates venv with `python3.11 -m venv --copies .venv`
  - Activates and installs deps via `pip install -e .` or `pip install -r requirements.txt`.
  - Validates Astrometry indexes are discoverable (run quick solve test).
- Provide a `systemd` unit file template `packaging/systemd/skysolve.service` for Raspbian, launching via absolute venv python path.

---

## Tests & CI
- Unit tests:
  - `tests/test_solver_adapter.py` — solve adapter mock tests (simulate success/failure/timeouts)
  - `tests/test_lx200_server.py` — verify command parsing and responses.
- Integration tests (run in CI with Astrometry install or mock):
  - `tests/integration_solve_flow.py` — mock camera image → solver → push to mock OnStep; assert OnStep received expected commands.
- CI considerations:
  - Avoid running full Astrometry solve in standard CI; use small unit mocks and optionally a special runner for full integration (self-hosted runner or docker image that includes astrometry indexes).
  - Build artifact/packaging job to produce tarball for Pi builds (or wheels if possible).
- Provide `tox` / `pytest` config for local runs.

---

## Observability & Logging
- Structured JSON logs at INFO/ERROR level (simple python `logging` with config). Include `solve_time_ms`, `solver`, `image_id` in logs.
- Debug logs for LX200 handler (socket connect/disconnect, commands received/parsed).
- Optional metrics endpoint `/metrics` (Prometheus text) for solve counts, solve duration histogram, OnStep push successes/failures.

---

## Security considerations
- Limit network exposure: default bind to `0.0.0.0` for convenience, but document how to bind to a specific interface (config `BIND_HOST`).
- Recommend using firewall rules (PF/iptables) when exposing ports on a public network. Include one-page guide in `docs/security.md`.
- LX200 server is readonly — explicitly document and enforce this in code to avoid accidental mount control.
- Consider authentication for web API if you expose it beyond local network (future work).

---

## Implementation checklist (concrete actions you can follow)
> These are *ordered* steps to achieve parity and then OnStep integration. Mark items done as you go.

1. Repo layout and docs
   - [x] Add `docs/` folder and move PRD + this Implementation Plan into `docs/` (this file: `docs/SKYSOLVE_NEXT_IMPLEMENTATION_PLAN.md`).
   - [x] Create `README.md` sections: ports, quickstart (venv, run), troubleshooting (firewall / PF), required Python version (3.11).
2. Stabilize runtime for Pi
   - [x] Update packaging to target Python 3.11 (update pyproject/README).
   - [x] Create `install_pi.sh` to create venv with `--copies` and install deps.  
   - [~] Add `systemd` unit template for autostart.  # Present in `services/`, but not in `packaging/systemd/` as specified.
3. Solver adapters
   - [x] Implement `solvers/solver_base.py` interface.
   - [~] Wrap Astrometry into `solvers/astrometry_adapter.py` (robust CLI wrapper, timeouts).  # Only a stub exists; real integration not done.
   - [~] Add `solvers/tetra_adapter.py` placeholder and research Tetra build options (binary vs pip wheel).  # Placeholder exists, full integration is a stretch goal.
4. Solve worker & API
   - [x] Implement solve worker to accept images (or accept demo image) and route to selected solver.
   - [x] Provide REST endpoint `POST /solve` (accept image, returns result).
   - [x] Add `GET /status` (show solver availability, last solve).
5. SkySafari / LX200 server
   - [x] Review and harden LX200 handler; ensure read-only semantics, robust parsing, and clear logs.
   - [x] Add config option for LX200 listen host and port (default `0.0.0.0:5002`).
6. OnStep client
   - [x] Implement `onstep/client.py` that accepts solver results and transmits appropriate OnStep commands.
   - [~] Add tests with a mock OnStep server in `tests/mocks` to validate commands.  # Mock server exists, test coverage may need review.
7. Web UI
   - [x] Build minimal UI for dashboard, solve trigger, solver selection, and settings; implement day/night mode CSS and toggle.
   - [ ] Add a small e2e test to exercise the UI solve flow (optional in CI).  # Not present.
8. Tests & CI
   - [x] Add unit tests + simple integration tests; include CI job matrix that runs lint + unit tests on Python 3.11.
   - [~] Lint, formatting, and coverage in CI.  # May lack full pre-commit/coverage integration.
9. Documentation & operations
   - [x] Add firewall troubleshooting doc (macOS PF example, `socketfilterfw` guidance).
   - [x] Add developer notes for recreating the venv (`venv --copies`) and common pitfalls (Homebrew Python vs venv).
   - [ ] Add PR template and contribution guidelines.  # May be missing or incomplete.

---

## Open questions (to resolve during planning)
- **Tetra packaging**: do we accept shipping a pre-built native binary for each architecture (x86_64, aarch64) or require building on target? (Recommended: build artifacts for Pi aarch64 and release them with project releases.)
- **Auto-hotspot**: built inside SkySolve or separate service? Recommendation: **separate service** (simpler to maintain and less privileged) — document integration points (health-check URL / Unix socket).
- **Authentication**: do we require web API auth from day one (e.g., basic token), or keep it local-only and add auth later? (Recommendation: local-only initially; add opt-in token auth in config for remote exposure.)

---

## Useful references & links
- Astrometry.net (project): https://astrometry.net/  
- OnStep official site / docs: https://on-step.sourceforge.net/  
- Tetra solver references (general): https://github.com/ctb/astrometry.net/tree/master/other/tetra  
- macOS Application Firewall `socketfilterfw` usage: https://ss64.com/osx/socketfilterfw.html  
- PF packet filter (macOS/FreeBSD): https://www.freebsd.org/cgi/man.cgi?query=pfctl&sektion=8

---

**Add this file to repo:** `docs/SKYSOLVE_NEXT_IMPLEMENTATION_PLAN.md`
