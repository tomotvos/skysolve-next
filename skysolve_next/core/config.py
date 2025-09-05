from pydantic_settings import BaseSettings
from pydantic import Field
import os
import json

class SolverSettings(BaseSettings):
    type: str = "astrometry"
    hint_timeout: int = 10
    solve_radius: float = 20.0
    plot: bool = False

class CameraSettings(BaseSettings):
    shutter_speed: str = "1"
    iso_speed: str = "1000"
    image_size: str = "1280x960"

class OnStepSettings(BaseSettings):
    host: str = "localhost"
    port: int = 9998
    enabled: bool = False

class Settings(BaseSettings):
    mode: str = Field(default="test")  # solve|align|demo|test
    web_port: int = 5001
    lx200_port: int = 5002
    solver: SolverSettings = Field(default_factory=SolverSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    onstep: OnStepSettings = Field(default_factory=OnStepSettings)

    _config_path = "skysolve_next/settings.json"
    _last_mtime = None

    def reload_if_changed(self):
        if not os.path.exists(self._config_path):
            # Create default settings.json if missing
            with open(self._config_path, "w") as f:
                json.dump(self.model_dump(), f, indent=2)
            self._last_mtime = os.path.getmtime(self._config_path)
            return
        mtime = os.path.getmtime(self._config_path)
        if self._last_mtime is None or mtime > self._last_mtime:
            with open(self._config_path, "r") as f:
                data = json.load(f)
            # Only update known fields
            for k, v in data.items():
                if hasattr(self, k):
                    field = getattr(self, k)
                    if isinstance(field, BaseSettings) and isinstance(v, dict):
                        for subk, subv in v.items():
                            if hasattr(field, subk):
                                setattr(field, subk, subv)
                    else:
                        setattr(self, k, v)
            self._last_mtime = mtime

    class Config:
        env_prefix = "SKYSOLVE_"
        case_sensitive = False

settings = Settings()
