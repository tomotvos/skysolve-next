import pytest
from fastapi.testclient import TestClient
from skysolve_next.web.app import app
import shutil
import os

client = TestClient(app)

WELL_KNOWN_IMAGE_PATH = "skysolve_next/web/solve/last_image.jpg"
TEST_IMAGE_PATH = "skysolve_next/web/static/demo.jpg"

@pytest.fixture(autouse=True)
def setup_test_image():
    # Ensure test image exists for tests
    if not os.path.exists(TEST_IMAGE_PATH):
        with open(TEST_IMAGE_PATH, "wb") as f:
            f.write(b"FAKEIMAGE")
    yield
    # Clean up well-known image after test
    if os.path.exists(WELL_KNOWN_IMAGE_PATH):
        os.remove(WELL_KNOWN_IMAGE_PATH)

def test_solve_test_image(monkeypatch):
    # Patch subprocess.run to simulate Astrometry.net output
    def fake_run(cmd, capture_output, text, timeout):
        class Result:
            returncode = 0
            stdout = "FAKE astrometry output\nRA,Dec = 123.45, 67.89"
            stderr = ""
        return Result()
    monkeypatch.setattr("subprocess.run", fake_run)
    response = client.post("/solve?test=1")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"
    log_text = "\n".join(data["log"])
    assert "solve-field command" in log_text
    assert "FAKE astrometry output" in log_text
    assert "Image solved" in log_text or "Image solved." in log_text


def test_solve_error(monkeypatch):
    # Patch subprocess.run to simulate failure
    def fake_run(cmd, capture_output, text, timeout):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "Simulated error"
        return Result()
    monkeypatch.setattr("subprocess.run", fake_run)
    response = client.post("/solve?test=1")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "error"
    log_text = "\n".join(data["log"])
    assert "Astrometry.net failed" in log_text
    # Message may be None if not set, but stderr should be present
    assert "Simulated error" in (data["message"] or "") or "Simulated error" in log_text
