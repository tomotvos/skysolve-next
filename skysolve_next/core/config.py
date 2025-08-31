from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    mode: str = Field(default="solve")  # solve|align|demo
    web_port: int = 5001
    solver_primary: str = "tetra3"      # tetra3|astrometry
    solver_fallback: str = "astrometry"
    onstep_enabled: bool = True
    onstep_host: str = "192.168.0.1"
    onstep_port: int = 9998
    onstep_sync_mode: str = "sync"      # sync|slew_then_sync

    class Config:
        env_prefix = "SKYSOLVE_"
        case_sensitive = False

settings = Settings()
