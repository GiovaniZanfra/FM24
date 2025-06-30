# fm24_selector/core/processing.py

import pandas as pd

from fm24_selector.utils.parsing import ROLE_TO_GENERIC, extract_positions_sides


def apply_threshold_rule(
    df: pd.DataFrame,
    score_column: str = "Highest Role Score",
    threshold_offset: float = 0.5
) -> pd.DataFrame:
    """
    Zera todos os scores abaixo de (score_column - threshold_offset).
    """
    df = df.copy()
    df["threshold"] = df[score_column] - threshold_offset

    num_cols = (
        df
        .select_dtypes(include=["float64", "int64"])
        .columns
        .difference([score_column])
    )

    for col in num_cols:
        df[col] = df.apply(
            lambda row: row[col] if row[col] >= row["threshold"] else 0,
            axis=1
        )

    return df.drop(columns="threshold")


def prepare_ratings(
    ratings: pd.DataFrame,
    formation: dict
) -> pd.DataFrame:
    """
    Seleciona apenas as colunas necessárias para o LP:
    'Name', 'Age' e cada posição de formation.
    Preenche NaNs com 0 e reseta o índice.
    """
    cols = ["Name", "Age"] + list(formation.keys())
    return ratings[cols].fillna(0).reset_index(drop=True)


def treat_transfer_value(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte a coluna 'Transfer Value' de strings como '£50M - 75M'
    ou '£200K' em colunas numéricas 'lower_bound', 'upper_bound' e 'mean_value'.
    """
    df = df.copy()

    # Remove símbolo "£"
    df["Transfer Value"] = df["Transfer Value"].str.replace("£", "", regex=False)

    # Separa em lower e upper (caso haja range)
    bounds = df["Transfer Value"].str.split(" - ", expand=True)
    df["lower_bound"] = bounds[0]
    df["upper_bound"] = bounds[1]

    # Converte sufixos M->e6, K->e3
    for col in ["lower_bound", "upper_bound"]:
        df[col] = (
            df[col]
            .str.replace("M", "e6", regex=False)
            .str.replace("K", "e3", regex=False)
            .str.replace(",", "", regex=False)
        )

    # Converte para float; se upper_bound for None, fica NaN
    df["lower_bound"] = pd.to_numeric(df["lower_bound"], errors="coerce")
    df["upper_bound"] = pd.to_numeric(df["upper_bound"], errors="coerce")

    # Se não havia upper_bound, copia lower_bound
    df["upper_bound"].fillna(df["lower_bound"], inplace=True)

    # Calcula valor médio
    df["mean_value"] = (
        df[["lower_bound", "upper_bound"]]
        .mean(axis=1)
    )

    return df


def filter_roles_by_position(
    df: pd.DataFrame,
    role_cols: list[str]
) -> pd.DataFrame:
    """
    Para cada jogador (linha), verifica a coluna 'Position' (string),
    extrai as posições genéricas que ele pode jogar, e zera todos
    os ratings cujas roles não estejam permitidas.
    """
    df = df.copy()
    for idx, row in df.iterrows():
        pos_str = row.get("Position") or row.get("Positions", "")
        allowed = extract_positions_sides(pos_str)
        # allowed é um dict { 'D':0/1, 'DM':0/1, ... }
        for col in role_cols:
            generic = ROLE_TO_GENERIC.get(col, "")
            if not generic or allowed.get(generic, 0) == 0:
                df.at[idx, col] = 0
    return df
