from fastapi import FastAPI, WebSocket, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
import os
import json

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

@app.post("/solve")
def solve(request: Request):
    # If demo requested, return demo image path
    if request.query_params.get("demo") == "1":
        return {"result": "success", "image_url": "/static/demo.jpg", "message": "Demo image loaded."}
    # Dummy response for upload
    return {"result": "success", "message": "Solve endpoint called."}

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
