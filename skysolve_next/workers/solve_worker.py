import time
import numpy as np
from skysolve_next.core.config import settings
from skysolve_next.solver.tetra3_solver import Tetra3Solver
from skysolve_next.solver.astrometry_solver import AstrometrySolver
from skysolve_next.mounts.onstep.lx200 import OnStepClient

def main():
    primary = Tetra3Solver() if settings.solver_primary == "tetra3" else AstrometrySolver()
    fallback = AstrometrySolver() if settings.solver_primary == "tetra3" else Tetra3Solver()
    onstep = OnStepClient() if settings.onstep_enabled else None

    while True:
        frame = np.zeros((256,256), dtype=np.uint8)  # TODO: real Picamera2 capture
        try:
            res = primary.solve(frame)
            if res.confidence < 0.7:
                res = fallback.solve(frame)
        except Exception:
            res = fallback.solve(frame)

        if onstep:
            try:
                if settings.onstep_sync_mode == "slew_then_sync":
                    onstep.slew_then_sync(res)
                else:
                    onstep.sync_pointing(res)
            except Exception:
                pass
        time.sleep(2)

if __name__ == "__main__":
    main()
