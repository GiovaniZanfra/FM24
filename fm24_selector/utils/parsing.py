# fm24_selector/utils/parsing.py

import re

import numpy as np
import pandas as pd

# possíveis posições e laterais
POSITIONS = ["D", "DM", "M", "AM", "WB", "GK", "ST"]
SIDES     = ["R", "L", "C"]

def parse_transfer_value(value: str) -> pd.Series:
    """
    Converte strings como '£50M - 75M', '£200K' ou 'Not for sale' em três valores numéricos:
    lower_bound, upper_bound e mean_value.
    """
    if not isinstance(value, str):
        return pd.Series([np.nan, np.nan, np.nan], index=["min", "max", "mean"])

    if value.strip().lower() == "not for sale":
        return pd.Series([np.nan, np.nan, np.nan], index=["min", "max", "mean"])

    # remove símbolo de libra e vírgulas
    clean = value.replace("£", "").replace(",", "").strip()

    # separa em range se houver " - "
    if " - " in clean:
        min_str, max_str = clean.split(" - ", 1)
    else:
        min_str = max_str = clean

    def to_number(s: str) -> float:
        s = s.strip().upper()
        if s.endswith("M"):
            return float(s[:-1]) * 1e6
        if s.endswith("K"):
            return float(s[:-1]) * 1e3
        try:
            return float(s)
        except ValueError:
            return np.nan

    low  = to_number(min_str)
    high = to_number(max_str)
    mean = np.nan if np.isnan(low) and np.isnan(high) else (np.nanmean([low, high]))

    return pd.Series([low, high, mean], index=["min", "max", "mean"])


def parse_wage(wage_str: str) -> float:
    """
    Converte strings de salário semanais tipo '£155,000 p/w' em valor numérico.
    Retorna None se não for possível parsear.
    """
    if not isinstance(wage_str, str):
        return None

    clean = wage_str.replace("£", "").replace(",", "").lower().replace(" p/w", "").strip()
    try:
        return float(clean)
    except ValueError:
        return None


def extract_positions_sides(pos: str) -> dict:
    """
    Dado um texto de posição (ex: 'DM (R)', 'AM/DM (L/C)'), retorna um dict:
      - chaves POSITIONS com 1 se presentes, 0 caso contrário
      - chaves SIDES    com 1 se presentes, 0 caso contrário

    Exemplos:
      extract_positions_sides("DM (R)")   -> {"D":0,"DM":1,...,"R":1,"L":0,"C":0}
      extract_positions_sides("AM/DM (L/C)")
    """
    # Extrai tokens de posição (ex: 'AM', 'DM')
    pos_tokens = re.findall(r"[A-Z]+(?:/[A-Z]+)?", pos)
    # Extrai dentro de parênteses (ex: 'L', 'C', 'L/C')
    side_tokens = re.findall(r"\((.*?)\)", pos)
    side_flags = "".join(side_tokens)

    # Mapeia presença de cada posição
    pos_dict = {p: int(any(p == token or p in token.split("/") for token in pos_tokens))
                for p in POSITIONS}
    # Mapeia presença de cada lado
    side_dict = {s: int(s in side_flags) for s in SIDES}

    return {**pos_dict, **side_dict}

# mapping de código de role → posição genérica (igual ao dicionário original)
ROLE_TO_GENERIC: dict[str, str] = {
    # Goalkeeper
    "gkd": "GK",
    "ska":"GK",
    "skd":"GK","sks":"GK",   
    # Defenders
    "fba": "D",  "fbd": "D",  "fbs": "D",
    "bpdc":"D", "bpdd":"D", "bpds":"D",
    "cdc": "D",  "cdd": "D",  "cds": "D",
    "ifbd":"D", "iwbd":"D", "ncbd":"D",
    "ncbc":"D", "ncbs":"D", "wcbd":"D", "wcbs":"D",
    "ld":  "D",  "ls":  "D", "iwbs":"D",
        "wba":"WB","wbWB":"WB","wbs":"WB",
    "wcba":"D","wcbd":"D","wcbs":"D",
    "cwbs":"WB", "cwba":"WB",


    # Defensive Midfielders
    "ad":  "DM", "bwmd":"DM","bwms":"DM",
    "dmd": "DM", "dms":"DM", "hbd":"DM",
    "regs":"DM",

    # Central Midfielders
    "apa": "M",  "aps":"AM",  "b2bs":"M",
    "cars":"M",  "cma":"M",  "cmd":"M",
    "cms": "M",  "dlpd":"DM", "dlps":"DM",
    "dwd": "M",  "dws":"M",  "engs":"AM",
    "meza":"M", "mezs":"M", "svs":"M",

    # Attacking Midfielders
    "ama": "AM", "ams":"AM", "f9s":"AM",
    "ifa": "AM", "ifs":"AM", "iwa":"AM",
    "iws":"AM", "rps":"DM", "ssa":"AM", "ws":"AM", "wa":"AM",

    # Forwards / Strikers
    "afa": "ST", "cfa":"ST", "cfs":"ST",
    "dlfa":"ST","dlfs":"ST","pa":"ST",
    "pfa":"ST","pfd":"ST","pfs":"ST",
    "raua":"ST","tfa":"ST",
    "tfs":"ST","trea":"ST","wtfa":"ST",
    "wtfs":"ST"
}