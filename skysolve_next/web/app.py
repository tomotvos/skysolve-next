from fastapi import FastAPI, WebSocket, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
from pydantic_settings import BaseSettings
import os
import json
import shutil
import subprocess
import re
import time
from threading import Lock
from skysolve_next.solver.astrometry_solver import AstrometrySolver
import logging

app = FastAPI(title="Skysolve Next", version="0.1.0")
app.mount("/static", StaticFiles(directory="skysolve_next/web/static"), name="static")

# Setup consistent logging
logger = logging.getLogger("skysolve.app")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.DEBUG)

STATUS = {"mode": "solve", "fps": 0.0, "last_conf": None}
LAST: SolveResult | None = None

@app.get("/status")
def status():
    settings.reload_if_changed()
    return {"mode": settings.mode, "fps": STATUS["fps"], "last_conf": STATUS["last_conf"]}

@app.post("/mode")
def set_mode(payload: dict = Body(...)):
    mode = payload.get("mode", "solve")
    STATUS["mode"] = mode
    settings.mode = mode
    # Save mode to settings.json
    import json
    with open("skysolve_next/settings.json", "r") as f:
        data = json.load(f)
    data["mode"] = mode
    with open("skysolve_next/settings.json", "w") as f:
        json.dump(data, f, indent=2)
    return STATUS

@app.get("/")
def ui():
    with open("skysolve_next/web/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/events")
async def events(ws: WebSocket):
    await ws.accept()
    await ws.send_json({"event": "hello", "port_web": settings.web_port})

@app.get("/static/demo.jpg")
def get_demo_image():
    return FileResponse("skysolve_next/web/static/demo.jpg")

WELL_KNOWN_IMAGE_PATH = "skysolve_next/web/solve/last_image.jpg"
DEMO_IMAGE_PATH = "skysolve_next/web/static/demo.jpg"
SOLVE_IMAGE_PATH = "skysolve_next/web/solve/image.jpg"
SOLVE_DIR = "skysolve_next/web/solve"

LAST_SOLVE = {
    "ra": None,
    "dec": None,
    "timestamp": None
}
DEFAULT_SOLVE_RADIUS = 20.0  # degrees


def write_status(mode, ra, dec, confidence, error=None):
    import time, json, os
    status_path = "skysolve_next/web/worker_status.json"
    # Load previous status if exists
    if os.path.exists(status_path):
        with open(status_path, "r") as f:
            prev = json.load(f)
    else:
        prev = {}
    # Only update timestamp and RA/Dec if mode is 'solve' and RA/Dec are not None
    if mode == "solve" and ra is not None and dec is not None:
        status = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "mode": mode,
            "ra": ra,
            "dec": dec,
            "confidence": confidence,
            "error": error
        }
    else:
        # Keep previous values for timestamp, ra, dec, confidence
        status = {
            "timestamp": prev.get("timestamp"),
            "mode": mode,
            "ra": prev.get("ra"),
            "dec": prev.get("dec"),
            "confidence": prev.get("confidence"),
            "error": error
        }
    with open(status_path, "w") as f:
        json.dump(status, f)

@app.post("/solve")
def solve(request: Request):
    global LAST_SOLVE
    settings.reload_if_changed()
    log_lines = []
    def log(msg):
        log_lines.append(str(msg))
    # Ensure solve directory exists
    os.makedirs(SOLVE_DIR, exist_ok=True)
    # If demo requested, copy demo image to solve path
    if request.query_params.get("demo") == "1" or request.query_params.get("test") == "1":
        shutil.copyfile(DEMO_IMAGE_PATH, SOLVE_IMAGE_PATH)
    image_path = SOLVE_IMAGE_PATH
    # Determine if we should use a hint
    now = time.time()
    hint = None
    hint_timeout = getattr(settings.solver, "hint_timeout", 10)
    solve_radius = getattr(settings.solver, "solve_radius", 20.0)
    if LAST_SOLVE["ra"] is not None and LAST_SOLVE["dec"] is not None and LAST_SOLVE["timestamp"] is not None:
        if now - LAST_SOLVE["timestamp"] <= hint_timeout:
            hint = {"ra": LAST_SOLVE["ra"], "dec": LAST_SOLVE["dec"]}
    # Unified solve workflow
    solver = AstrometrySolver()
    start_time = time.time()
    try:
        result = solver.solve(image_path, ra_hint=hint["ra"] if hint else None, dec_hint=hint["dec"] if hint else None, radius_hint=solve_radius, log=log)
        ra_deg = result.ra_deg
        dec_deg = result.dec_deg
        confidence = result.confidence
        returncode = 0
        stderr = None
    except Exception as e:
        ra_deg = dec_deg = confidence = None
        returncode = 1
        stderr = str(e)
    elapsed = time.time() - start_time
    mode = STATUS.get("mode", "solve")
    error = stderr if returncode is None or returncode != 0 else None
    write_status(mode, ra_deg, dec_deg, confidence, error)
    if returncode is None or returncode != 0:
        return {"result": "error", "message": stderr, "log": log_lines}
    # Save last solve info
    LAST_SOLVE["ra"] = ra_deg
    LAST_SOLVE["dec"] = dec_deg
    LAST_SOLVE["timestamp"] = now
    logger.info(f"[{time.strftime('%H:%M:%S')}] Image solved. Total solve time: {elapsed:.2f} seconds.")
    return {
        "result": "success",
        "image_url": f"/solve/image.jpg",
        "ra": ra_deg,
        "dec": dec_deg,
        "confidence": confidence,
        "message": f"Image solved. Total solve time: {elapsed:.2f} seconds.",
        "log": log_lines
    }

@app.get("/solve/image.jpg")
def get_solve_image():
    return FileResponse(SOLVE_IMAGE_PATH)

@app.get("/solve")
def get_solve_image_legacy():
    return FileResponse(SOLVE_IMAGE_PATH)

@app.post("/onstep/push")
def push_onstep():
    # Dummy response for OnStep push
    return {"result": "success", "message": "OnStep push endpoint called."}

@app.post("/auto-solve")
def auto_solve(payload: dict):
    # Dummy response for auto-solve toggle
    enabled = payload.get("enabled", False)
    return {"result": "success", "auto_solve": enabled}

@app.post("/auto-push")
def auto_push(payload: dict):
    # Dummy response for auto-push toggle
    enabled = payload.get("enabled", False)
    return {"result": "success", "auto_push": enabled}

@app.get("/settings")
def get_settings():
    settings.reload_if_changed()
    # Return as dict for API compatibility
    return settings.model_dump()

@app.post("/settings")
def update_settings(new_settings: dict = Body(...)):
    # Merge each section instead of overwriting
    settings.reload_if_changed()
    for section, values in new_settings.items():
        if hasattr(settings, section):
            current = getattr(settings, section)
            # If it's a nested Pydantic model and values is a dict, merge fields
            if isinstance(current, BaseSettings) and isinstance(values, dict):
                for k, v in values.items():
                    # Special case for onstep.enabled: always cast to bool
                    if section == "onstep" and k == "enabled":
                        setattr(current, k, bool(v) if not isinstance(v, bool) else v)
                    elif hasattr(current, k):
                        setattr(current, k, v)
            else:
                setattr(settings, section, values)
    # Special case: ensure onstep.enabled is always merged, even if only 'enabled' is present
    if 'onstep' in new_settings and isinstance(new_settings['onstep'], dict):
        if 'enabled' in new_settings['onstep']:
            settings.onstep.enabled = bool(new_settings['onstep']['enabled'])
    # Save to settings.json
    import json
    # Only dump nested structure, not flattened keys
    def settings_dump():
        return {
            "mode": settings.mode,
            "web_port": settings.web_port,
            "lx200_port": settings.lx200_port,
            "solver": settings.solver.model_dump(),
            "camera": settings.camera.model_dump(),
            "onstep": settings.onstep.model_dump()
        }
    with open("skysolve_next/settings.json", "w") as f:
        json.dump(settings_dump(), f, indent=2)
    return settings_dump()

@app.get("/worker-status")
def worker_status():
    status_path = "skysolve_next/web/worker_status.json"
    if not os.path.exists(status_path):
        return {"error": "No worker status available"}
    with open(status_path, "r") as f:
        status = json.load(f)
    # If worker is not running, set error even if file exists but is stale
    import psutil
    worker_running = any(
        any(
            'solve_worker.py' in arg or 'skysolve_next/workers/solve_worker.py' in arg
            for arg in (p.info.get('cmdline') or [])
        )
        for p in psutil.process_iter(['cmdline'])
    )
    if not worker_running:
        status['error'] = 'No worker status available'
    return status
