from fastapi import FastAPI, WebSocket, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
import os
import json
import shutil
import subprocess
import re
import time
from skysolve_next.solver.astrometry_solver import AstrometrySolver

app = FastAPI(title="Skysolve Next", version="0.1.0")
app.mount("/static", StaticFiles(directory="skysolve_next/web/static"), name="static")

STATUS = {"mode": "solve", "fps": 0.0, "last_conf": None}
LAST: SolveResult | None = None

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")
DEFAULT_SETTINGS = {
    "camera": {
        "shutter_speed": "1",
        "iso_speed": "1000",
        "image_size": "1280x960"
    },
    "solver": {
        "type": "astrometry"
    },
    "onstep": {
        "host": "localhost",
        "port": 5002
    }
}

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        return DEFAULT_SETTINGS.copy()
    with open(SETTINGS_PATH, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

SETTINGS = load_settings()

@app.get("/status")
def status():
    return {"mode": STATUS["mode"], "fps": STATUS["fps"], "last_conf": STATUS["last_conf"]}

@app.post("/mode")
def set_mode(mode: str):
    STATUS["mode"] = mode
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

WELL_KNOWN_IMAGE_PATH = "skysolve_next/web/static/last_image.jpg"
DEMO_IMAGE_PATH = "skysolve_next/web/static/demo.jpg"
SOLVE_IMAGE_PATH = "skysolve_next/web/solve/image.jpg"
SOLVE_DIR = "skysolve_next/web/solve"

def run_solve(image_path, log):
    solver = AstrometrySolver()
    start_time = time.time()
    cmd = [solver.solve_field_path, image_path, "--overwrite", "--no-plots"]
    log(f"[{time.strftime('%H:%M:%S')}] solve-field command: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=solver.timeout)
    for line in proc.stdout.splitlines():
        log(f"[{time.strftime('%H:%M:%S')}] {line}")
    if proc.stderr:
        for line in proc.stderr.splitlines():
            log(f"[{time.strftime('%H:%M:%S')}] {line}")
    if proc.returncode != 0:
        log(f"[{time.strftime('%H:%M:%S')}] Astrometry.net failed: {proc.stderr}")
        return None, None, None, None, None, time.time() - start_time
    # Parse stdout for RA, Dec, Confidence
    ra_deg = dec_deg = confidence = 0.0
    for line in proc.stdout.splitlines():
        # Remove timestamp prefix if present
        line_no_ts = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", line)
        m1 = re.search(r"RA,Dec\s*=\s*\(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
        m2 = re.search(r"Field center: \(RA,Dec\) = \(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
        if m1:
            try:
                ra_deg = float(m1.group(1))
                dec_deg = float(m1.group(2))
            except Exception:
                pass
        elif m2:
            try:
                ra_deg = float(m2.group(1))
                dec_deg = float(m2.group(2))
            except Exception:
                pass
        if "Confidence:" in line_no_ts:
            try:
                confidence = float(line_no_ts.split()[1])
            except Exception:
                pass
    elapsed = time.time() - start_time
    return ra_deg, dec_deg, confidence, proc.returncode, proc.stderr, elapsed

@app.post("/solve")
def solve(request: Request):
    log_lines = []
    def log(msg):
        log_lines.append(str(msg))
    # Ensure solve directory exists
    os.makedirs(SOLVE_DIR, exist_ok=True)
    # If demo requested, copy demo image to solve path
    if request.query_params.get("demo") == "1":
        shutil.copyfile(DEMO_IMAGE_PATH, SOLVE_IMAGE_PATH)
    image_path = SOLVE_IMAGE_PATH
    # Unified solve workflow
    ra_deg, dec_deg, confidence, returncode, stderr, elapsed = run_solve(image_path, log)
    if returncode is None or returncode != 0:
        return {"result": "error", "message": stderr, "log": log_lines}
    log(f"[{time.strftime('%H:%M:%S')}] Image solved. Total solve time: {elapsed:.2f} seconds.")
    return {
        "result": "success",
        "image_url": f"/solve/image.jpg",
        "ra": ra_deg,
        "dec": dec_deg,
        "confidence": confidence,
        "message": f"Image solved. Total solve time: {elapsed:.2f} seconds.",
        "log": log_lines
    }

@app.get("/solve")
def get_solve_image():
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
    return SETTINGS

@app.post("/settings")
def update_settings(new_settings: dict = Body(...)):
    global SETTINGS
    # Merge each section instead of overwriting
    for section, values in new_settings.items():
        if section in SETTINGS and isinstance(values, dict):
            SETTINGS[section].update(values)
        else:
            SETTINGS[section] = values
    save_settings(SETTINGS)
    return SETTINGS
