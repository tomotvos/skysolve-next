import pytest
from fastapi.testclient import TestClient
from skysolve_next.web.app import app
import shutil
import os

client = TestClient(app)

WELL_KNOWN_IMAGE_PATH = "skysolve_next/web/static/last_image.jpg"
DEMO_IMAGE_PATH = "skysolve_next/web/static/demo.jpg"

@pytest.fixture(autouse=True)
def setup_demo_image():
    # Ensure demo image exists for tests
    if not os.path.exists(DEMO_IMAGE_PATH):
        with open(DEMO_IMAGE_PATH, "wb") as f:
            f.write(b"FAKEIMAGE")
    yield
    # Clean up well-known image after test
    if os.path.exists(WELL_KNOWN_IMAGE_PATH):
        os.remove(WELL_KNOWN_IMAGE_PATH)

def test_solve_demo_image(monkeypatch):
    # Patch subprocess.run to simulate Astrometry.net output
    def fake_run(cmd, capture_output, text, timeout):
        class Result:
            returncode = 0
            stdout = "FAKE astrometry output\nRA,Dec = 123.45, 67.89"
            stderr = ""
        return Result()
    monkeypatch.setattr("subprocess.run", fake_run)
    response = client.post("/solve?demo=1")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"
    assert "solve-field command" in "\n".join(data["log"])
    assert "FAKE astrometry output" in "\n".join(data["log"])
    assert "Demo image solved." in "\n".join(data["log"])

def test_solve_error(monkeypatch):
    # Patch subprocess.run to simulate failure
    def fake_run(cmd, capture_output, text, timeout):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "Simulated error"
        return Result()
    monkeypatch.setattr("subprocess.run", fake_run)
    response = client.post("/solve?demo=1")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "error"
    assert "Astrometry.net failed" in "\n".join(data["log"])
    assert "Simulated error" in data["message"]
