from abc import ABC, abstractmethod
import numpy as np
from skysolve_next.core.models import SolveResult

class Solver(ABC):
    @abstractmethod
    def solve(self, image: np.ndarray) -> SolveResult: ...
