import numpy as np
from skysolve_next.solver.base import Solver
from skysolve_next.core.models import SolveResult

class Tetra3Solver(Solver):
    def __init__(self) -> None:
        pass

    def solve(self, image: np.ndarray) -> SolveResult:
        return SolveResult(ra_deg=180.0, dec_deg=45.0, roll_deg=0.0, plate_scale_arcsec_px=12.3, confidence=0.95)
