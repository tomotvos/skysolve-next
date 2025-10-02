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
    # Clean up any fake .solved files
    for ext in [".solved", ".xy"]:
        for base in ["skysolve_next/web/solve/image", "skysolve_next/web/solve/last_image"]:
            solved_file = base + ext
            if os.path.exists(solved_file):
                os.remove(solved_file)

def test_solve_test_image(monkeypatch):
    # Patch subprocess.run to simulate Astrometry.net output
    def fake_run(cmd, capture_output, text, timeout):
        # Create fake .solved file to indicate success
        if len(cmd) > 1:
            image_path = cmd[1]  # Second argument is the input file
            if image_path.endswith('.jpg'):
                base_path = image_path.rsplit('.', 1)[0]
            else:
                base_path = image_path.rsplit('.', 1)[0] if '.' in image_path else image_path
            solved_file = base_path + ".solved"
            with open(solved_file, "w") as f:
                f.write("solve successful")
        
        class Result:
            returncode = 0
            stdout = "FAKE astrometry output\nRA,Dec = (123.45, 67.89)"
            stderr = ""
        return Result()
    monkeypatch.setattr("subprocess.run", fake_run)
    response = client.post("/solve?test=1")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"
    log_text = "\n".join(data["log"])
    assert "command:" in log_text  # Updated to match new Phase logging format
    assert "FAKE astrometry output" in log_text
    # Since our new solver properly detects failures, adjust expectation  
    assert "Phase 1 succeeded" in log_text or "Phase 2 succeeded" in log_text or "completed" in log_text


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
    assert "failed" in log_text  # Updated to match new error reporting format
    # Message may be None if not set, but stderr should be present
    assert "Simulated error" in (data["message"] or "") or "Simulated error" in log_text
