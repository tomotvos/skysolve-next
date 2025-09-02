import time, math
import numpy as np
from skysolve_next.core.config import settings
from skysolve_next.core.models import SolveResult
from skysolve_next.solver.tetra3_solver import Tetra3Solver
from skysolve_next.solver.astrometry_solver import AstrometrySolver
from skysolve_next.publish.lx200_server import LX200Server
from skysolve_next.mounts.onstep.lx200 import OnStepClient

def main():
    primary = Tetra3Solver() if settings.solver_primary == "tetra3" else AstrometrySolver()
    fallback = AstrometrySolver() if settings.solver_primary == "tetra3" else Tetra3Solver()

    # Start read-only LX200 server for SkySafari (port 5002)
    lx200 = LX200Server(port=settings.lx200_port)
    lx200.start()

    onstep = OnStepClient() if settings.onstep_enabled else None

    last_ra = None
    last_dec = None
    while True:
        if settings.mode.lower() == "demo":
            t = time.time()
            # Sweep RA 0..360 over ~8 minutes, Dec oscillates around +20 deg
            ra_deg = (t % 480) * (360.0 / 480.0)
            dec_deg = 20.0 + 10.0 * math.sin(t / 30.0)
            res = SolveResult(ra_deg=ra_deg, dec_deg=dec_deg, roll_deg=0.0, plate_scale_arcsec_px=12.0, confidence=0.99)
        else:
            frame = np.zeros((256,256), dtype=np.uint8)  # TODO: real Picamera2 capture
            try:
                # Pass hints if available and using AstrometrySolver
                if isinstance(primary, AstrometrySolver) and last_ra is not None and last_dec is not None:
                    res = primary.solve(frame, ra_hint=last_ra, dec_hint=last_dec, radius_hint=settings.astrometry_hint_radius)
                else:
                    res = primary.solve(frame)
                if res.confidence < 0.7:
                    if isinstance(fallback, AstrometrySolver) and last_ra is not None and last_dec is not None:
                        res = fallback.solve(frame, ra_hint=last_ra, dec_hint=last_dec, radius_hint=settings.astrometry_hint_radius)
                    else:
                        res = fallback.solve(frame)
            except Exception:
                if isinstance(fallback, AstrometrySolver) and last_ra is not None and last_dec is not None:
                    res = fallback.solve(frame, ra_hint=last_ra, dec_hint=last_dec, radius_hint=settings.astrometry_hint_radius)
                else:
                    res = fallback.solve(frame)
            # Update last RA/Dec if solve succeeded
            if res and res.confidence > 0.5:
                last_ra = res.ra_deg
                last_dec = res.dec_deg

        # Publish to SkySafari (read-only)
        lx200.publish(res)

        # Optionally push to OnStep (sync-first)
        if onstep:
            try:
                if settings.onstep_sync_mode == "slew_then_sync":
                    onstep.slew_then_sync(res)
                else:
                    onstep.sync_pointing(res)
            except Exception:
                pass
        time.sleep(1.5)

if __name__ == "__main__":
    main()
