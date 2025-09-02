import os
import subprocess
import json
import logging
from skysolve_next.solver.base import Solver
from skysolve_next.core.models import SolveResult

class AstrometrySolver(Solver):
    def __init__(self, solve_field_path: str = "solve-field", timeout: int = 60, max_retries: int = 2) -> None:
        self.solve_field_path = solve_field_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger("AstrometrySolver")

    def solve(self, image_path: str, ra_hint: float = None, dec_hint: float = None, radius_hint: float = None) -> SolveResult:
        if not (isinstance(image_path, str) and os.path.isfile(image_path)):
            self.logger.error(f"Invalid image path: {image_path}")
            raise ValueError("AstrometrySolver expects a valid image file path.")
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                cmd = [self.solve_field_path, image_path, "--overwrite", "--no-plots"]
                # Add hint parameters if provided
                if ra_hint is not None and dec_hint is not None and radius_hint is not None:
                    cmd += ["--ra", str(ra_hint), "--dec", str(dec_hint), "--radius", str(radius_hint)]
                    self.logger.info(f"Using hint: RA={ra_hint}, Dec={dec_hint}, Radius={radius_hint}")
                self.logger.info(f"solve-field command: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
                if proc.returncode != 0:
                    self.logger.warning(f"Astrometry.net failed (attempt {attempt}): {proc.stderr}")
                    raise RuntimeError(f"Astrometry.net failed: {proc.stderr}")
                # Parse stdout for solution summary
                ra_deg = dec_deg = roll_deg = plate_scale_arcsec_px = confidence = 0.0
                for line in proc.stdout.splitlines():
                    if "RA,Dec =" in line:
                        try:
                            parts = line.split()
                            ra_deg = float(parts[2].replace(',', ''))
                            dec_deg = float(parts[3].replace(',', ''))
                        except Exception:
                            pass
                    if "Field rotation:" in line:
                        try:
                            roll_deg = float(line.split()[2])
                        except Exception:
                            pass
                    if "Pixel scale:" in line:
                        try:
                            plate_scale_arcsec_px = float(line.split()[2])
                        except Exception:
                            pass
                    if "Confidence:" in line:
                        try:
                            confidence = float(line.split()[1])
                        except Exception:
                            pass
                self.logger.info(f"Astrometry.net solve succeeded on attempt {attempt}")
                return SolveResult(
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    roll_deg=roll_deg,
                    plate_scale_arcsec_px=plate_scale_arcsec_px,
                    confidence=confidence
                )
            except Exception as e:
                self.logger.error(f"Astrometry.net solve error (attempt {attempt}): {e}")
                last_exception = e
        self.logger.critical(f"Astrometry.net failed after {self.max_retries} attempts: {last_exception}")
        raise RuntimeError(f"Astrometry.net failed after {self.max_retries} attempts: {last_exception}")
