import os
import json
from skysolve_next.core.config import settings

def test_settings_file_location():
    # Remove root-level settings.json if it exists
    if os.path.exists("settings.json"):
        os.remove("settings.json")
    assert not os.path.exists("settings.json")
    assert os.path.exists(settings._config_path)
    assert settings._config_path == "skysolve_next/settings.json"

def test_settings_structure():
    with open(settings._config_path, "r") as f:
        data = json.load(f)
    # Top-level keys
    assert "solver" in data and isinstance(data["solver"], dict)
    assert "camera" in data and isinstance(data["camera"], dict)
    assert "onstep" in data and isinstance(data["onstep"], dict)
    # No duplicate/flattened keys
    for k in ["onstep_enabled", "onstep_host", "onstep_port", "onstep_sync_mode"]:
        assert k not in data
    # Nested keys
    assert "enabled" in data["onstep"]
    assert "host" in data["onstep"]
    assert "port" in data["onstep"]

def test_settings_update_only_correct_location():
    # Remove root-level settings.json if it exists
    if os.path.exists("settings.json"):
        os.remove("settings.json")
    # Simulate settings update
    settings.mode = "align"
    with open(settings._config_path, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)
    # Validate only correct file exists
    assert os.path.exists(settings._config_path)
    assert not os.path.exists("settings.json")
    # Restore
    settings.mode = "solve"
    with open(settings._config_path, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)

def test_settings_update_and_save():
    # Remove root-level settings.json if it exists
    if os.path.exists("settings.json"):
        os.remove("settings.json")
    # Update top-level and nested settings
    settings.mode = "align"
    settings.solver.type = "tetra3"
    settings.solver.hint_timeout = 99
    settings.camera.shutter_speed = "2"
    settings.onstep.enabled = True
    settings.onstep.host = "192.168.1.100"
    settings.onstep.port = 1234
    # Save
    with open(settings._config_path, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)
    # Reload and check
    settings.reload_if_changed()
    with open(settings._config_path, "r") as f:
        data = json.load(f)
    assert data["mode"] == "align"
    assert data["solver"]["type"] == "tetra3"
    assert data["solver"]["hint_timeout"] == 99
    assert data["camera"]["shutter_speed"] == "2"
    assert data["onstep"]["enabled"] is True
    assert data["onstep"]["host"] == "192.168.1.100"
    assert data["onstep"]["port"] == 1234
    # Restore
    settings.mode = "solve"
    settings.solver.type = "astrometry"
    settings.solver.hint_timeout = 10
    settings.camera.shutter_speed = "1"
    settings.onstep.enabled = False
    settings.onstep.host = "localhost"
    settings.onstep.port = 9998
    with open(settings._config_path, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)
