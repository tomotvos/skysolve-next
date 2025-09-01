from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
