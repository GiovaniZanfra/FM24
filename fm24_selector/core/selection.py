# fm24_selector/core/selection.py

import json
import math

import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value

from fm24_selector.core.processing import apply_threshold_rule, filter_roles_by_position


def get_best(ratings: pd.DataFrame,
             pos_qtd_dict: dict,
             age_constraint: int = None,
             full_team: bool = False):
    """
    Resolve o PL para selecionar melhores jogadores.
    """
    pq = pos_qtd_dict.copy()
    if full_team:
        pq = {pos: qtd * 2 for pos, qtd in pq.items()}

    ratings = ratings.reset_index(drop=True)
    players = range(len(ratings))
    positions = list(pq.keys())

    prob = LpProblem(name="Player_Selection", sense=LpMaximize)
    x = LpVariable.dicts("x", (players, positions), 0, 1, cat="Binary")

    # Objetivo
    prob += lpSum(ratings.loc[i, p] * x[i][p]
                  for i in players for p in positions)

    # Cada jogador numa só posição
    for i in players:
        prob += lpSum(x[i][p] for p in positions) <= 1

    # Pelo menos 1 em cada posição
    for p in positions:
        prob += lpSum(x[i][p] for i in players) >= 1

    # Quantidade máxima por posição
    for p, q in pos_qtd_dict.items():
        prob += lpSum(x[i][p] for i in players) <= q

    if age_constraint is not None:
        total = sum(pos_qtd_dict.values())
        # calcula o número mínimo de slots que devem ter idade ≤ age_constraint
        half = math.ceil(total / 2)

        prob += (
            lpSum(
                x[i][p]
                for i in players
                for p in positions
                if ratings.loc[i, "Age"] <= age_constraint
            )
            >= half
        ), "Median_Age_Constraint"

    # Total de jogadores >= soma das quantidades
    prob += lpSum(x[i][p] for i in players for p in positions) >= sum(pos_qtd_dict.values())

    prob.solve()

    selected = []
    for i in players:
        for p in positions:
            if value(x[i][p]) == 1:
                selected.append({
                    "name":  ratings.loc[i, "Name"],
                    "position": p,
                    "score": ratings.loc[i, p]
                })

    return selected, value(prob.objective)


def get_best_from_json(json_path: str,
                       club: str,
                       formation: dict,
                       players_to_remove: list = None,
                       age_constraint: int = None,
                       threshold: float = 0.5,
                       use_positions: bool = False,
                       national_squad: bool = False):
    """
    Carrega JSON, filtra, aplica threshold, opcionalmente filtra roles por posição,
    e retorna 3 equipes (first, second, third).
    """
    players_to_remove = players_to_remove or []

    # 1) Leitura do JSON e DataFrame
    with open(json_path, 'r') as f:
        data = json.load(f)["data"]
    df = pd.DataFrame(data)

    # 2) Filtra clube e remoções
    if national_squad:
        df = df.query("Nat == @club and Name not in @players_to_remove")
    else:
        df = df.query("Club == @club and Name not in @players_to_remove")

    # 3) Threshold de scores
    df = apply_threshold_rule(df, threshold_offset=threshold)

    # 4) Filtrar roles incompatíveis com a posição real
    if use_positions and formation:
        df = filter_roles_by_position(df, list(formation.keys()))

    # 5) Geração dos 3 melhores times
    teams = []
    remaining = df.copy()
    for _ in range(3):
        selected, _ = get_best(remaining, formation, age_constraint)
        team_df = pd.DataFrame(selected)
        print(team_df)
        teams.append(team_df)
        remaining = remaining[~remaining["Name"].isin(team_df["name"])]

    return teams[0], teams[1], teams[2]


def get_players_for_position(
    json_path: str,
    club: str,
    formation: dict,
    score_threshold: float,
    use_positions: bool = False,
    national_squad: bool = False
):
    """
    Para cada role em formation, lista (Name,Score) ordenados.
    Se `use_positions=True`, zera também as roles incompatíveis com a posição real.
    """
    # 1) Carrega JSON e filtra clube
    with open(json_path, 'r') as f:
        data = json.load(f)["data"]
    if national_squad:
        df = pd.DataFrame(data).query("Nat == @club")
    else:
        df = pd.DataFrame(data).query("Club == @club")

    # 2) Threshold de scores
    df = apply_threshold_rule(df, threshold_offset=score_threshold)

    # 3) (Opcional) Filtra roles por posição real
    if use_positions and formation:
        df = filter_roles_by_position(df, list(formation.keys()))

    # 4) Agrupa por role e retorna lista de (Name,Score)
    result = {}
    for role in formation:
        df_role = df[df[role] != 0].sort_values(role, ascending=False)
        result[role] = list(zip(df_role["Name"], df_role[role]))

    return result