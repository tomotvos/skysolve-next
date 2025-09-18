from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Literal
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

class LogRotationSettings(BaseSettings):
    max_file_size_mb: int = 10
    backup_count: int = 5

class LoggingSettings(BaseSettings):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    structured: bool = False  # Enable JSON structured logging
    rotation: LogRotationSettings = Field(default_factory=LogRotationSettings)

class Settings(BaseSettings):
    mode: str = Field(default="test")  # solve|align|demo|test
    web_port: int = 5001
    lx200_port: int = 5002
    log_level: str = Field(default="INFO")  # Backward compatibility
    solver: SolverSettings = Field(default_factory=SolverSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    onstep: OnStepSettings = Field(default_factory=OnStepSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    _config_path = "skysolve_next/settings.json"
    _last_mtime = None

    def reload_if_changed(self):
        # Import here to avoid circular imports
        from skysolve_next.core.logging_config import set_log_level
        
        if not os.path.exists(self._config_path):
            # Create default settings.json if missing
            with open(self._config_path, "w") as f:
                json.dump(self.model_dump(), f, indent=2)
            self._last_mtime = os.path.getmtime(self._config_path)
            return
        mtime = os.path.getmtime(self._config_path)
        if self._last_mtime is None or mtime > self._last_mtime:
            old_log_level = getattr(self.logging, 'level', self.log_level)
            
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
            
            # Update log level dynamically if it changed
            new_log_level = getattr(self.logging, 'level', self.log_level)
            if old_log_level != new_log_level:
                set_log_level(new_log_level)
            
            self._last_mtime = mtime

    def save(self):
        """Save current settings to file"""
        with open(self._config_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)
        self._last_mtime = os.path.getmtime(self._config_path)

    class Config:
        env_prefix = "SKYSOLVE_"
        case_sensitive = False

settings = Settings()
