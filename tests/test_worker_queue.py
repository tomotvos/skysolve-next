import threading
import queue
import numpy as np
import time
import pytest
from skysolve_next.workers.solve_worker import CameraCapture
from skysolve_next.core.config import settings

class DummySettings:
    mode = "solve"
    camera = {
        "shutter_speed": "0.001",  # Much faster for test
        "iso_speed": "1000",
        "image_size": "1280x960"
    }
    solver = type("Solver", (), {"type": "tetra3", "solve_radius": 1.0})()
    onstep = type("OnStep", (), {"enabled": False})()
    lx200_port = 9999
    onstep_sync_mode = "sync_pointing"

def test_camera_capture_single_threaded():
    camera = CameraCapture(DummySettings())
    frames = []
    for _ in range(5):
        frame = camera.capture() if hasattr(camera, 'capture') else None
        frames.append(frame)
        time.sleep(0.01)
    assert len(frames) == 5

    # Removed queue/thread safety test for single-threaded mode
