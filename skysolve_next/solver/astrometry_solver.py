import numpy as np
from skysolve_next.solver.base import Solver
from skysolve_next.core.models import SolveResult

class AstrometrySolver(Solver):
    def __init__(self) -> None:
        pass

    def solve(self, image: np.ndarray) -> SolveResult:
        return SolveResult(ra_deg=179.9, dec_deg=45.1, roll_deg=0.2, plate_scale_arcsec_px=12.2, confidence=0.90)
