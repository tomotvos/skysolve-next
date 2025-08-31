from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult

app = FastAPI(title="Skysolve Next", version="0.1.0")
app.mount("/static", StaticFiles(directory="skysolve_next/web/static"), name="static")

STATUS = {"mode": "solve", "fps": 0.0, "last_conf": None}
LAST: SolveResult | None = None

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
