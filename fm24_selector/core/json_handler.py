# fm24_selector/core/json_handler.py

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from fm24_selector.config import BASE_PATH, MONTH_MAP
from fm24_selector.core.processing import apply_threshold_rule, filter_roles_by_position


def get_json_path(team, month="latest", year="latest"):
    path = Path(BASE_PATH) / team
    files = []
    for f in path.glob("*.json"):
        stem = f.stem
        m = MONTH_MAP[stem[:-4].lower()]
        y = int(stem[-4:])
        files.append((datetime(y, m, 1), f))

    if month != "latest":
        files = [tup for tup in files if tup[1].stem.lower().startswith(month.lower())]
    if year != "latest":
        files = [tup for tup in files if tup[0].year == int(year)]

    selected = max(files, key=lambda x: x[0])[1]
    return selected


def load_squad(
    json_path: Path,
    club: str,
    players_to_remove: list[str] | None = None,
    threshold: float = 0.5,
    formation: dict[str,int] | None = None,
    use_positions: bool = False
) -> pd.DataFrame:
    """
    Carrega o JSON, filtra por clube e remoções, aplica threshold,
    e (opcionalmente) zera roles incompatíveis com a posição real.
    """
    players_to_remove = players_to_remove or []

    # 1) ler JSON
    with open(json_path, 'r') as f:
        data = json.load(f)["data"]
    df = pd.DataFrame(data)

    # 2) filtrar clube e remoções
    df = df.query("Club == @club and Name not in @players_to_remove")

    # 3) zerar scores abaixo do threshold
    df = apply_threshold_rule(df, threshold_offset=threshold)

    # 4) se quiser filtrar por posição, zerar roles não permitidas
    if use_positions and formation:
        df = filter_roles_by_position(df, list(formation.keys()))

    return df
