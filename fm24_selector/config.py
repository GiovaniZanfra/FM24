# config.py
from pathlib import Path

# Configurations and constants
formations = {
    "Corinthians": {"gkd":1, "wbs":1, "cwbs":1, "bpdd":1, "cdd":1, "cma":1, "cmd":1, "cars":1, "ssa":1, "afa":1, "cfa":1},
    "São Paulo": {"ska":1, "bpdd":1, "bpdc":1, "wbs":1, "wba":1, "dlpd":1, "rps":1, "wa":1, "iws":1, "aps":1, "cfa":1},
    "Palmeiras": {"skd":1, "bpdd":2, "fba":2, "bwms":2, "iwa":2, "engs":1, "pa":1},
    "Santos": {"sks":1, "bpdd":3, "wbs":2, "dlps":1, "dms":1, "ams":2, "afa":1},
    "BRA": {"skd":1, "bpdd":2, "fba":2, "bwms":2, "iwa":2, "engs":1, "pa":1},
}

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
    'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

BASE_PATH = Path(__file__).parent.parent / "data"
