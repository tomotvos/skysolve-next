from dataclasses import dataclass
from typing import Union

@dataclass
class SolveResult:
    ra_deg: float
    dec_deg: float
    roll_deg: float
    plate_scale_arcsec_px: float
    confidence: Union[float, str]
