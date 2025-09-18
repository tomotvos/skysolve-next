import socket
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
from skysolve_next.core.logging_config import get_logger

class OnStepClient:
    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or settings.onstep.host
        self.port = port or settings.onstep.port
        self.logger = get_logger("onstep_client", "mount")

    def _send(self, cmd: str) -> None:
        with socket.create_connection((self.host, self.port), timeout=3) as s:
            s.sendall(cmd.encode())

    def sync_pointing(self, result: SolveResult) -> None:
        # Set RA/Dec then sync (:CM#)
        self.logger.info(f"Syncing OnStep pointing: RA={result.ra_deg}, Dec={result.dec_deg}")
        self._send(f":Sr{self._format_ra(result.ra_deg)}#")
        self._send(f":Sd{self._format_dec(result.dec_deg)}#")
        self._send(":CM#")
        self.logger.info("OnStep sync completed")

    def slew_then_sync(self, result: SolveResult) -> None:
        # Slew to solved coords, then sync
        self.logger.info(f"OnStep slew then sync: RA={result.ra_deg}, Dec={result.dec_deg}")
        self._send(f":Sr{self._format_ra(result.ra_deg)}#")
        self._send(f":Sd{self._format_dec(result.dec_deg)}#")
        self._send(":MS#")
        # TODO: wait/poll until slew complete, then sync
        self._send(":CM#")
        self.logger.info("OnStep slew and sync completed")

    @staticmethod
    def _format_ra(ra_deg: float) -> str:
        hours = ra_deg / 15.0
        h = int(hours); m = int((hours - h) * 60); s = int((((hours - h) * 60) - m) * 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def _format_dec(dec_deg: float) -> str:
        sign = "+" if dec_deg >= 0 else "-"; v = abs(dec_deg)
        d = int(v); m = int((v - d) * 60); s = int((((v - d) * 60) - m) * 60)
        return f"{sign}{d:02d}*{m:02d}:{s:02d}"
