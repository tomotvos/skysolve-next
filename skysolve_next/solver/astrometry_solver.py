import os
import subprocess
import json
import logging
from skysolve_next.solver.base import Solver
from skysolve_next.core.models import SolveResult
from skysolve_next.core.logging_config import get_logger

class AstrometrySolver(Solver):
    def __init__(self, solve_field_path: str = "solve-field", timeout: int = 60, max_retries: int = 2) -> None:
        self.solve_field_path = solve_field_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_logger("astrometry_solver", "solver")

    def solve(self, image_path: str, ra_hint: float = None, dec_hint: float = None, radius_hint: float = None, log=None) -> SolveResult:
        import re, time, json
        def _log(msg, level="INFO"):
            if log:
                log_msg = json.dumps({
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
                    "level": level,
                    "msg": msg
                })
                log(log_msg)
            getattr(self.logger, level.lower(), self.logger.info)(msg)

        if not (isinstance(image_path, str) and os.path.isfile(image_path)):
            _log(f"Invalid image path: {image_path}", level="ERROR")
            raise ValueError("AstrometrySolver expects a valid image file path.")
        start_time = time.time()
        if radius_hint is None:
            radius_hint = 20.0
        cmd = [
            self.solve_field_path,
            image_path,
            "--overwrite",
            "--no-plots",
            "--new-fits", "none"
        ]
        if ra_hint is not None and dec_hint is not None:
            cmd += ["--ra", str(ra_hint), "--dec", str(dec_hint), "--radius", str(radius_hint)]
            _log(f"Using hint: RA={ra_hint}, Dec={dec_hint}, Radius={radius_hint}")
        _log(f"solve-field command: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        for line in proc.stdout.splitlines():
            _log(line, level="DEBUG")
        if proc.stderr:
            for line in proc.stderr.splitlines():
                _log(line, level="ERROR")
        if proc.returncode != 0:
            _log(f"Astrometry.net failed: {proc.stderr}", level="ERROR")
            raise RuntimeError(f"Astrometry.net failed: {proc.stderr}")
        ra_deg = dec_deg = confidence = 0.0
        for line in proc.stdout.splitlines():
            line_no_ts = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", line)
            m1 = re.search(r"RA,Dec\s*=\s*\(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
            m2 = re.search(r"Field center: \(RA,Dec\) = \(([-\d.]+),\s*([-\d.]+)\)", line_no_ts)
            if m1:
                try:
                    ra_deg = float(m1.group(1))
                    dec_deg = float(m1.group(2))
                except Exception:
                    pass
            elif m2:
                try:
                    ra_deg = float(m2.group(1))
                    dec_deg = float(m2.group(2))
                except Exception:
                    pass
            if "Confidence:" in line_no_ts:
                try:
                    confidence = float(line_no_ts.split()[1])
                except Exception:
                    pass
        elapsed = time.time() - start_time
        _log(f"Astrometry.net solve succeeded in {elapsed:.2f}s: RA={ra_deg}, DEC={dec_deg}, CONF={confidence}")
        # Add summary log for compatibility with app expectations, including solve time
        _log(
            f"Image solved. Solve time: {elapsed:.2f} seconds.", level="INFO"
        )
        return SolveResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            roll_deg=None,
            plate_scale_arcsec_px=None,
            confidence=confidence if confidence not in (None, 0.0) else "-"
        )
