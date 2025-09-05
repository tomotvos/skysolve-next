import pytest
import numpy as np
from skysolve_next.workers.solve_worker import CameraCapture
from skysolve_next.core.config import settings

class DummySettings:
    camera = {
        "shutter_speed": "1",
        "iso_speed": "1000",
        "image_size": "1280x960"
    }

@pytest.fixture
def camera():
    return CameraCapture(DummySettings())

def test_mock_capture(camera):
    frame = camera.capture()
    assert isinstance(frame, np.ndarray)
    # Accept any valid image shape, but prefer test image shape if available
    assert frame.ndim == 2  # Grayscale
    assert frame.shape[0] > 100 and frame.shape[1] > 100  # Should be a real image size
    # Should update preview and latest_frame
    assert camera.get_latest_frame() is not None
    assert camera.get_last_error() is None or isinstance(camera.get_last_error(), str)

def test_error_handling(monkeypatch, camera):
    # Simulate error in save_preview
    def fail_save_preview(frame):
        raise Exception("Save failed")
    camera.save_preview = fail_save_preview
    frame = camera.capture()
    assert isinstance(frame, np.ndarray)
    # Should still update latest_frame
    assert camera.get_latest_frame() is not None
    # Error should be set
    assert camera.get_last_error() is not None


def test_thread_safety(camera):
    import threading
    results = []
    def worker():
        for _ in range(10):
            frame = camera.capture()
            results.append(frame is not None)
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(results)
    # Should not raise race condition
    assert camera.get_latest_frame() is not None
