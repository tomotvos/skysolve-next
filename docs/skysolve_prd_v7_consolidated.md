# Skysolve Next — PRD v7 (Consolidated Baseline)

> **Scope:** Establish feature parity with legacy SkySolve for **SkySafari display** via a **read‑only LX200 server**, while also supporting an optional **OnStep client** path that syncs solved coordinates to the controller. Keep the Web UI on **5001** and SkySafari/LX200 on **5002**. Include a **demo mode** so the system is testable without a solver or hardware.

---

## 1) Goals & Non‑Goals

### Goals
1. **Parity with SkySolve**
   - App runs in **Solve mode** and publishes the **current solved pointing** to clients.
   - **SkySafari** can connect and display pointing via **LX200/TCP** (no telescope motion).
2. **OnStep Client (optional)**
   - After each successful solve, optionally **sync** to OnStep (`:Sr`, `:Sd`, `:CM#`).
   - SkySafari may independently control the mount via OnStep (typically on port 9999).
3. **Modernized scaffold**
   - Clean Python packaging, typed code, FastAPI Web/UI, systemd units, mDNS, and a “demo” path for quick verification.

### Non‑Goals
- The app **does not** move the telescope via the LX200 server (read‑only).
- The app **does not** manage Wi‑Fi/AP itself (handled by a separate service).

---

## 2) Operating Modes

- **Solve** (default): capture → plate solve → publish RA/Dec to LX200; optional **OnStep sync**.
- **Demo**: no capture/solver; generate a smooth RA/Dec sweep to exercise SkySafari and the UI.
- **Align** (placeholder): fast capture/no solve (future; out of scope for v7).

---

## 3) System Architecture (high‑level)

**Processes**
- **Web/API** (FastAPI/Uvicorn) on **port 5001**; serves UI and provides `/status` and config endpoints.
- **Worker** process:
  - Acquires frames (Picamera2 on Pi; mock frames on macOS).
  - Runs **solver pipeline** (Astrometry.net default; Tetra3/Cedar fast path on Pi).
  - Publishes the latest **SolveResult** to:
    - **LX200 server** (read‑only) on **port 5002**, and
    - **OnStep client** (optional) on **9998** (sync‑first).
- **LX200 server** (TCP): a small threaded server embedded in the worker that responds to SkySafari queries.

**Networking & Service Discovery**
- **mDNS/Avahi:**
  - `_http._tcp` on **5001** → “Skysolve Next Web”
  - `_lx200._tcp` on **5002** → “Skysolve Next LX200”

**Hotspot**
- Managed by an external service (NetworkManager + GPIO trigger). The app only **reads** current network status.

---

## 4) Interfaces

### 4.1 Web/UI (5001)
- `GET /` → simple status UI with **day/night** theme (night = muted red tones).
- `GET /status` → JSON: mode, fps, last confidence, last RA/Dec, OnStep sync state.
- `WS /events` → stream solve/sync events (for live UI updates).
- (future) `POST /config` → update settings (host/ports/mode) safely.

### 4.2 LX200 Server (5002, read‑only)
- TCP server responding to **Meade LX200** commands.
- **Supported (query):**
  - `:GR#` → Right Ascension `HH:MM:SS#`
  - `:GD#` → Declination `sDD*MM:SS#` (sign, degrees, arcminutes, arcseconds)
  - Identity/housekeeping (optional but helpful): `:GVP#`, `:GVN#`, `:GVD#`, `:GVT#`, `:GC#`, `:GL#`, `:U#` (ack)
- **Accepted but ignored (ack only):** `:SC`, `:SL`, `:St`, `:Sg` (return success code as expected)
- **Ignored (no motion):** `:MS#`, `:Mn#`, `:Me#`, `:Ms#`, `:Mw#` (return neutral, e.g., `0` or `#`)
- **Stream parser** handles **batched** and **partial** commands per TCP read.

> **Design rule:** The LX200 server must **never slew** the mount. It only reports position from the latest `SolveResult` (or a demo sweep).

### 4.3 OnStep Client (optional; default **disabled** in v7)
- TCP to OnStep **port 9998** (leaves **9999** free for SkySafari).
- **Sync‑first flow:**
  1. `:Srhh:MM:SS#` (set RA)
  2. `:Sd±DD*MM:SS#` (set Dec)
  3. `:CM#` (synchronize)
- **Slew‑then‑sync** (optional policy): add `:MS#` and wait/poll before `:CM#`.
- **Safety:** configurable max angular delta to auto‑sync; otherwise require manual action or use slew‑then‑sync policy.

---

## 5) Configuration

**Environment file** (`/etc/skysolve-next.env`) — defaults chosen for side‑by‑side with legacy SkySolve:
```
SKYSOLVE_MODE=solve
SKYSOLVE_WEB_PORT=5001
SKYSOLVE_LX200_PORT=5002

# Solvers
SKYSOLVE_SOLVER_PRIMARY=tetra3        # 'tetra3' or 'astrometry'
SKYSOLVE_SOLVER_FALLBACK=astrometry

# OnStep (optional; disabled by default in v7 baseline)
SKYSOLVE_ONSTEP_ENABLED=false         # set true to enable sync
SKYSOLVE_ONSTEP_HOST=192.168.0.1
SKYSOLVE_ONSTEP_PORT=9998
SKYSOLVE_ONSTEP_SYNC_MODE=sync        # 'sync' | 'slew_then_sync'
SKYSOLVE_SYNC_MAX_DEG=5.0             # safety threshold for auto-sync
```

**Platform guards (pyproject deps):**
- `gpiozero`, `picamera2`, `cedar-solve` only on **Linux**.
- Python target: **3.11** (Pi Bookworm parity).

---

## 6) Solvers

- **Primary:** **Astrometry.net** (robust; calls `solve-field`, parses WCS to RA/Dec/scale/rotation).
- **Fast path:** **Tetra3/Cedar** on Pi (lower latency; database initialization at startup).
- **Fallback logic:** If primary confidence < threshold or times out → try the other.
- **Demo mode:** Generates a smooth RA/Dec sweep (no external solver required) to verify LX200/SkySafari and UI wiring quickly.

---

## 7) Capture

- **Pi (field):** Picamera2/libcamera; exposure, gain/ISO, ROI/binning; cadence ~2–5s.
- **macOS (dev):** mock frames or demo sweep.
- Provide a small **preview** image for UI display.

---

## 8) System Integration (Pi)

- **systemd** services:
  - `skysolve-next.service` → worker (capture/solve, publish to LX200, optional OnStep sync)
  - `skysolve-next-web.service` → Uvicorn/FastAPI on **5001**
- **Avahi/mDNS**:
  - `/etc/avahi/services/skysolve-next-http.service` → `_http._tcp` 5001
  - `/etc/avahi/services/skysolve-next-lx200.service` → `_lx200._tcp` 5002
- **Install root:** `/opt/skysolve-next` with venv at `/opt/skysolve-next/.venv`.
- **Config:** `/etc/skysolve-next.env`

---

## 9) UX & UI

- Minimal status page: last RA/Dec, plate scale, confidence, mode, OnStep status.
- **Day/Night** toggle; night uses muted **red** palette.
- Live updates via `/events` WebSocket.

---

## 10) Diagnostics & Logging

- Structured logs for: solver results, LX200 command sampling, OnStep sync attempts/outcomes.
- `/status` includes uptime, fps, last confidence, last RA/Dec, last sync delta/outcome.
- Option to download recent logs via UI (post‑v7).

---

## 11) Security

- Web binds `0.0.0.0` for convenience; consider basic auth or CORS limits (future).
- LX200 server exposes pointing only; no motion commands honored.

---

## 12) Acceptance Criteria

1. **SkySafari parity**
   - With `SKYSOLVE_MODE=demo` or with an installed solver, SkySafari connects to **port 5002** as **Meade LX200 Classic** and continuously reads RA/Dec via `:GR#`, `:GD#`.
   - The server responds correctly to **batched** commands (`:U#`, identity, date/time) and never slews.
2. **OnStep client (optional)**
   - With `SKYSOLVE_ONSTEP_ENABLED=true`, each successful solve leads to an OnStep **sync** (`:Sr`, `:Sd`, `:CM#`) on **9998**; SkySafari (if connected to OnStep on **9999**) reflects improved pointing.
3. **Side‑by‑side readiness**
   - Web on **5001** and LX200 on **5002** run without interfering with legacy SkySolve.
4. **Pi field run**
   - On a Pi 4/5, both systemd services start; mDNS advertises both services.

---

## 13) Open Questions

- Default **equinox**/frame for RA/Dec values (JNow vs J2000) and whether to precess on output to OnStep and/or LX200.
- Default **SYNC_MAX_DEG** and behavior when exceeded (block vs slew‑then‑sync policy).
- Minimum command set SkySafari expects beyond `:GR#`/`:GD#` (current list seems sufficient; confirm in testing).

---

## 14) References
- Original SkySolve - https://github.com/githubdoe/skysolve
- Meade LX200 Command Set — https://www.meade.com/support/LX200CommandSet.pdf
- OnStep wiki: Connections & ports — https://onstep.groups.io/g/main/wiki/3863
- OnStep Software WiFi Server ports (9996–9999) — https://onstep.groups.io/g/main/wiki/26881
- Astrometry.net docs — http://astrometry.net/doc/
- Picamera2 Manual — https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf
- FastAPI — https://fastapi.tiangolo.com/
- Uvicorn — https://www.uvicorn.org/
