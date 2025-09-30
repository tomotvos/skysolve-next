import os
import json
import shutil
import subprocess
import re
import time
import logging
import asyncio
import threading
from threading import Lock
from fastapi import FastAPI, WebSocket, Request, Body, status as http_status, HTTPException, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
from pydantic_settings import BaseSettings
from skysolve_next.solver.astrometry_solver import AstrometrySolver
from skysolve_next.core.logging_config import get_logger, get_recent_logs, add_log_listener, remove_log_listener

# --- Core app and globals ---
app = FastAPI(title="Skysolve Next", version="0.1.0")
app.mount("/static", StaticFiles(directory="skysolve_next/web/static"), name="static")

# Serve the main UI at root
@app.get("/", response_class=HTMLResponse)
def root():
    try:
        with open("skysolve_next/web/templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>Error loading UI: {e}</h1>", status_code=500)

# Setup consistent logging using centralized configuration
logger = get_logger("web_app", "web")

# Initialize logging and generate a startup message
# Temporarily commented out to test deadlock theory
# logger.info("SkySolve Next web application starting up")

# Shared status globals
STATUS = {"mode": "solve", "fps": 0.0, "last_conf": None}
LAST_SOLVE = {"ra": None, "dec": None, "timestamp": None}

# Middleware to reload settings dynamically (log level is handled in config.py)
@app.middleware("http")
async def reload_settings_middleware(request: Request, call_next):
    settings.reload_if_changed()
    response = await call_next(request)
    return response

DEMO_IMAGE_PATH = "skysolve_next/web/static/demo.jpg"
SOLVE_IMAGE_PATH = "skysolve_next/web/solve/image.jpg"
SOLVE_DIR = "skysolve_next/web/solve"

LAST_SOLVE = {
    "ra": None,
    "dec": None,
    "timestamp": None
}
DEFAULT_SOLVE_RADIUS = 20.0  # degrees


def get_demo_image():
    return FileResponse(DEMO_IMAGE_PATH)

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

from fastapi import HTTPException

@app.get("/solve/image.jpg")
def get_solve_image():
    import os
    if not os.path.exists(SOLVE_IMAGE_PATH):
        raise HTTPException(status_code=404, detail="Solve image not found.")
    return FileResponse(SOLVE_IMAGE_PATH)

@app.get("/solve")
def get_solve_image_legacy():
    import os
    if not os.path.exists(SOLVE_IMAGE_PATH):
        raise HTTPException(status_code=404, detail="Solve image not found.")
    return FileResponse(SOLVE_IMAGE_PATH)



# System control endpoints (shutdown/restart)
@app.post("/system/shutdown", status_code=http_status.HTTP_202_ACCEPTED)
def system_shutdown():
    import sys
    if not sys.platform.startswith("linux"):
        return {"result": "error", "message": "Shutdown only supported on Linux."}
    try:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        return {"result": "success", "message": "Shutdown command sent."}
    except Exception as e:
        return {"result": "error", "message": str(e)}

@app.post("/system/restart", status_code=http_status.HTTP_202_ACCEPTED)
def system_restart():
    import sys
    if not sys.platform.startswith("linux"):
        return {"result": "error", "message": "Restart only supported on Linux."}
    try:
        subprocess.Popen(["sudo", "reboot"])
        return {"result": "success", "message": "Restart command sent."}
    except Exception as e:
        return {"result": "error", "message": str(e)}

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
    
    try:
        with open(status_path, "r") as f:
            status = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"error": f"Cannot read worker status: {e}"}
    
    # Check if status file is recent (updated within last 30 seconds)
    # This is more reliable than process detection for systemd services
    try:
        import time
        file_mtime = os.path.getmtime(status_path)
        current_time = time.time()
        file_age = current_time - file_mtime
        
        if file_age > 30:  # File is stale (older than 30 seconds)
            status['error'] = 'Worker status file is stale - worker may not be running'
        
    except OSError:
        status['error'] = 'Cannot check worker status file timestamp'
    
    return status

@app.get("/status")
def get_status():
    """Get current application status including mode"""
    settings.reload_if_changed()
    return {
        "mode": settings.mode,
        "status": "running"
    }

@app.post("/mode")
def set_mode(payload: dict = Body(...)):
    """Set the application mode"""
    mode = payload.get("mode")
    if mode not in ["solve", "align", "test"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    settings.reload_if_changed()
    settings.mode = mode
    settings.save()
    logger.info(f"Application mode changed to: {mode}")
    return {"result": "success", "mode": mode}

@app.get("/logs")
def get_logs(count: int = 100):
    """Get recent log entries"""
    print(f"DEBUG: /logs endpoint called with count={count}")
    try:
        logs = get_recent_logs(count)
        print(f"DEBUG: Retrieved {len(logs)} log entries")
        return {"logs": logs}
    except Exception as e:
        print(f"DEBUG: Error getting logs: {e}")
        import traceback
        traceback.print_exc()
        return {"logs": [], "error": str(e)}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()
    logger.info("Log streaming WebSocket connected")
    
    # Queue to receive new log entries
    log_queue = asyncio.Queue()
    
    # Callback function to add new logs to the queue
    def log_listener(log_entry):
        try:
            # Use put_nowait to avoid blocking the logging thread
            log_queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            # If queue is full, skip this log entry
            pass
    
    try:
        # Add listener for new log entries
        add_log_listener(log_listener)
        
        # Send recent logs first
        recent_logs = get_recent_logs(50)
        for log_entry in recent_logs:
            await websocket.send_json(log_entry)
        
        # Stream new log entries in real-time
        while True:
            try:
                # Wait for new log entry or check if connection is still alive
                log_entry = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                await websocket.send_json(log_entry)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except WebSocketDisconnect:
                    break
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up listener
        remove_log_listener(log_listener)
        logger.info("Log streaming WebSocket disconnected")
