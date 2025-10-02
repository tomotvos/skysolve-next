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

    def _is_solve_successful(self, ra_deg, dec_deg, base_path):
        """Check if solve result is valid by checking .solved file and RA/Dec values"""
        solved_file = base_path + ".solved"
        
        # Check if .solved file exists (most reliable indicator)
        solved_exists = os.path.exists(solved_file)
        
        # Check if RA/Dec are valid numbers
        coords_valid = (ra_deg is not None and dec_deg is not None and 
                       ra_deg != 0.0 and dec_deg != 0.0)
        
        return solved_exists and coords_valid

    def solve(self, image_path: str, ra_hint: float = None, dec_hint: float = None, radius_hint: float = None, log=None, enable_fallback: bool = True) -> SolveResult:
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
        
        overall_start_time = time.time()
        if radius_hint is None:
            radius_hint = 20.0
        
        # Get base path without extension for temporary files
        base_path = os.path.splitext(image_path)[0]
        xy_path = base_path + ".xy"
        
        # Phase 1: Always solve the image file (with hints if provided) and generate xy file
        has_hints = ra_hint is not None and dec_hint is not None
        
        if has_hints:
            _log(f"Phase 1: Solving image with hints - RA={ra_hint}, Dec={dec_hint}, Radius={radius_hint}")
        else:
            _log("Phase 1: Solving image without hints")
            
        # Always generate xy file for potential Phase 2 use
        cmd = self._build_solve_command(image_path, base_path, ra_hint, dec_hint, radius_hint, keep_xy=True)
        phase1_result = self._execute_solve_field(cmd, base_path, _log, "Phase 1")
        
        if self._is_solve_successful(phase1_result.ra_deg, phase1_result.dec_deg, base_path):
            elapsed = time.time() - overall_start_time
            _log(f"Phase 1 succeeded in {elapsed:.2f}s: RA={phase1_result.ra_deg}, DEC={phase1_result.dec_deg}, CONF={phase1_result.confidence}")
            return phase1_result
        else:
            _log("Phase 1 failed or returned invalid coordinates", level="WARNING")
        
        # Phase 2: Fallback solve using xy file without hints (only if fallback enabled)
        if enable_fallback:
            _log("Phase 2: Retrying without hints using xy file")
            
            # Check if xy file exists from Phase 1
            if not os.path.exists(xy_path):
                _log(f"XY file {xy_path} not found, fallback not possible", level="ERROR")
                elapsed = time.time() - overall_start_time
                _log(f"Solve failed in {elapsed:.2f}s - no fallback available", level="ERROR")
                return phase1_result
            
            _log(f"Using xy file: {xy_path}")
            # Build an unhinted solve command
            cmd = self._build_solve_command(xy_path, base_path)
            result = self._execute_solve_field(cmd, base_path, _log, "Phase 2")
            elapsed = time.time() - overall_start_time
            
            if self._is_solve_successful(result.ra_deg, result.dec_deg, base_path):
                _log(f"Phase 2 succeeded in {elapsed:.2f}s: RA={result.ra_deg}, DEC={result.dec_deg}, CONF={result.confidence}")
            else:
                _log(f"Phase 2 completed in {elapsed:.2f}s but was unsuccessful", level="WARNING")
            
            return result
        else:
            # Fallback disabled, return Phase 1 result
            elapsed = time.time() - overall_start_time
            _log(f"Fallback disabled. Solve failed in {elapsed:.2f}s", level="ERROR")
            return phase1_result

    def _build_solve_command(self, input_path: str, base_path: str, ra_hint: float = None, dec_hint: float = None, radius_hint: float = None, keep_xy: bool = False):
        """Build solve-field command with common parameters and optional hints"""
        cmd = [
            self.solve_field_path,
            input_path,
            "--overwrite",
            "--no-plots",
            "--new-fits", "none",
            "--sigma", "5",
            "--depth", "20",
            "--uniformize", "0",
            "--no-remove-lines",
            "--match", "none",
            "--corr", "none",
            "--rdls", "none"
        ]
        
        # Add hint parameters if provided
        if ra_hint is not None and dec_hint is not None:
            cmd.extend(["--ra", str(ra_hint), "--dec", str(dec_hint), "--radius", str(radius_hint)])
        
        # Add keep-xylist if requested
        if keep_xy:
            xy_path = base_path + ".xy"
            cmd.extend(["--keep-xylist", xy_path])
        
        return cmd

    def _execute_solve_field(self, cmd, base_path, _log, phase_name):
        """Execute solve-field command and parse results"""
        import re, time
        
        phase_start_time = time.time()
        _log(f"{phase_name} command: {' '.join(cmd)}")
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            for line in proc.stdout.splitlines():
                _log(line, level="DEBUG")
            if proc.stderr:
                for line in proc.stderr.splitlines():
                    _log(line, level="ERROR")
            
            if proc.returncode != 0:
                _log(f"{phase_name} failed with return code {proc.returncode}: {proc.stderr}", level="ERROR")
                # Don't raise exception, return zero result to allow fallback
                return SolveResult(ra_deg=0.0, dec_deg=0.0, roll_deg=None, plate_scale_arcsec_px=None, confidence=0.0)
            
            # Parse results
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
            
            phase_elapsed = time.time() - phase_start_time
            _log(f"{phase_name} completed in {phase_elapsed:.2f}s: RA={ra_deg}, DEC={dec_deg}, CONF={confidence}")
            
            return SolveResult(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                roll_deg=None,
                plate_scale_arcsec_px=None,
                confidence=confidence if confidence not in (None, 0.0) else "-"
            )
            
        except subprocess.TimeoutExpired:
            _log(f"{phase_name} timed out after {self.timeout} seconds", level="ERROR")
            return SolveResult(ra_deg=0.0, dec_deg=0.0, roll_deg=None, plate_scale_arcsec_px=None, confidence=0.0)
        except Exception as e:
            _log(f"{phase_name} failed with exception: {e}", level="ERROR")
            return SolveResult(ra_deg=0.0, dec_deg=0.0, roll_deg=None, plate_scale_arcsec_px=None, confidence=0.0)

    def _cleanup_temp_files(self, base_path: str):
        """Clean up temporary files generated by solve-field"""
        temp_extensions = [".xy", ".xyls", ".axy", ".match", ".rdls", ".solved", ".wcs"]
        for ext in temp_extensions:
            temp_file = base_path + ext
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                self.logger.warning(f"Could not remove temporary file {temp_file}: {e}")
