# Skysolve Next — PRD (OnStep Sync-First) — v5

## 1. Overview
Skysolve Next is a Raspberry Pi–based application that continuously captures the night sky, plate-solves images, and **synchronizes** a connected **OnStep** mount controller with the solved coordinates. **SkySafari connects directly to OnStep** for GoTo and control; Skysolve Next is **not** an LX200 server for SkySafari.

This version supersedes v4 by removing the internal LX200 server. The app acts as an **OnStep client**: after each successful solve it pushes the solved RA/Dec to OnStep and issues a **sync**. Side-by-side operation with legacy SkySolve is preserved by keeping the Web/API on **port 5001**.

---

## 2. Key Changes vs v4
- **Removed** internal LX200 server (previously on port 5002).  
- **Web/API remains on 5001** (mDNS `_http._tcp`).  
- **OnStep integration** is now the primary output path: **RA/Dec → OnStep → `:CM` sync** (optionally `slew_then_sync`).  
- **mDNS** no longer advertises LX200; only the Web API/UI is advertised.  

---

## 3. Objectives
- Robust, testable Python app with dual plate solvers (**Astrometry.net** default, **Tetra3/Cedar** fast option).  
- Day/Night web UI and REST API on **5001** for status, configuration and diagnostics.  
- Clean system integration via **systemd**; safe to run **alongside** the legacy SkySolve.  
- **Separate hotspot manager** (NetworkManager + GPIO7) outside the app.  
- **OnStep sync-first** workflow; optional **slew-then-sync** policy for specific use cases.

---

## 4. Functional Requirements

### 4.1 Camera Capture
- Picamera2/libcamera capture on Pi (exposure, gain/ISO, binning, ROI).  
- Adjustable cadence (~1–10s).  
- Provide JPEG/PNG preview for UI.

### 4.2 Plate Solving
- **Astrometry.net** (default; robust).  
- **Tetra3/Cedar** (fast path).  
- Return RA/Dec, roll, plate scale, confidence.  
- Retry/backoff; fallback to the other solver when confidence < threshold.

### 4.3 OnStep Integration (Primary)
- **Connection:** TCP to OnStep (default **host** configurable; default **port 9998** recommended for software clients; SkySafari typically uses **9999** separately).  
- **Sync flow (default):** After a successful plate solve,
  1. `:Srhh:MM:SS#` (set RA)  
  2. `:Sd±DD*MM:SS#` (set Dec)  
  3. `:CM#` (**synchronization**)  
- **Optional flow:** `slew_then_sync` → `:Sr`, `:Sd`, `:MS#` (slew), then `:CM#` when settled.  
- **Coordinate frame:** configurable **equinox** (default **of-date/JNow**); precession/apparent corrections applied if required by OnStep settings.  
- **Safety thresholds:** configurable max position delta for sync; if exceeded, require user confirmation or apply `slew_then_sync`.  
- **Resilience:** auto-retry on transient socket errors; exponential backoff; visible connection status in UI.

### 4.4 Web API & UI (Port 5001)
- **REST API** (FastAPI): `/status`, `/mode`, `/config`, `/onstep/status`, `/onstep/test-sync` (dry-run).  
- **Web UI**: day/night theme; show last solve, OnStep connection state, and “Sync now” (manual).  
- **Events (WS)**: stream solve events and OnStep sync outcomes.

### 4.5 Modes of Operation
- **Solve Mode:** capture → solve → (policy) sync with OnStep.  
- **Align Mode:** rapid capture, no solve (star field/centroids display).  
- **Demo Mode:** playback stored frames (no hardware).

### 4.6 Networking & AP (Separate Service)
- NetworkManager profiles for **Home** and **Field (AP)**; GPIO7 toggle at boot.  
- Skysolve reads current IP/SSID; does **not** manage Wi‑Fi state.

### 4.7 System Integration
- **systemd** units (side-by-side safe):  
  - `skysolve-next.service` (worker: capture/solve/sync)  
  - `skysolve-next-web.service` (API/UI on 5001)  
- **mDNS/Avahi**: advertise `_http._tcp` on 5001 only.  
- Install root `/opt/skysolve-next`, env file `/etc/skysolve-next.env`.

### 4.8 Diagnostics & Logging
- Structured logs; log OnStep commands and results (rate-limited).  
- `/status` exposes cadence, confidence, uptime, last sync result.  
- UI can download recent logs.

### 4.9 Test & Demo
- Unit tests for solver adapters and OnStep client (`sync`, `slew_then_sync`).  
- Demo images for offline testing.  
- GitHub Actions CI: lint, type-check, tests.

---

## 5. Non-Functional Requirements
- Python **3.11** (Pi Bookworm parity), typed codebase.  
- FastAPI, Uvicorn.  
- Platform-guard Pi-only deps (`picamera2`, `gpiozero`, `cedar-solve`) to Linux.  
- Packaging: PEP 621 (`pyproject.toml`).

---

## 6. Acceptance Criteria
- Fresh install on Pi 4/5 (64‑bit) runs UI on **5001** and performs repeated **solve → sync** with OnStep.  
- SkySafari connects to **OnStep directly** (e.g., 9999) and reflects improvements after Skysolve syncs.  
- Safe sync policy enforced (delta thresholds; optional `slew_then_sync`).  
- Network AP/Home toggle works via separate service.  
- Demo mode functional without hardware.  
- Side-by-side with legacy SkySolve without port/service conflicts.

---

## 7. Open Questions
- Default equinox handling: assume **of-date/JNow** unless configured?  
- Minimum/maximum delta before allowing automatic sync?  
- Should the UI offer a “three-star quick sync” helper (batch of solves across the sky)?

---

## 8. References
- OnStep group wiki (connections/ports): https://onstep.groups.io/g/main/wiki/3863  
- OnStep ports & Software WiFi Server notes (9996–9999 usage): https://onstep.groups.io/g/main/wiki/26881  
- Typical SkySafari-to-OnStep setup discussion (examples): https://www.cloudynights.com/topic/724964-instein-g11-onstep-kit-installation-story/  
- LX200 command set (sync via `:CM#`): https://www.meade.com/support/LX200CommandSet.pdf
