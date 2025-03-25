from typing import Optional
import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value
import json
import logging
from functools import wraps
import re
import numpy as np
from colorama import Fore, Style
from glob import glob

def suppress_logs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Save the current logging level
        logging_level = logging.getLogger().getEffectiveLevel()
        # Suppress all logging
        logging.getLogger().setLevel(logging.CRITICAL)
        try:
            return func(*args, **kwargs)
        finally:
            # Restore the original logging level
            logging.getLogger().setLevel(logging_level)
    return wrapper



@suppress_logs
def get_best(ratings ,pos_qtd_dict, age_constraint=None, full_team = False): 
    pos_qtd_dict_ = pos_qtd_dict
    if full_team:

        for k, val in pos_qtd_dict_.items():
            pos_qtd_dict_[k] = val*2

    ratings = ratings.reset_index(drop=True)
    # Define the linear programming problem
    prob = LpProblem(name="Player_Selection", sense=LpMaximize)

    # Define binary variables
    players = range(len(ratings))
    x = LpVariable.dicts("x", (players, list(pos_qtd_dict_.keys())), 0, 1, cat="Binary")

    # Objective function
    prob += lpSum(ratings.loc[player, position] * x[player][position] for player in players for position in list(pos_qtd_dict_.keys()))

    # Constraints
    for player in players:
        prob += lpSum(x[player][position] for position in list(pos_qtd_dict_.keys())) <= 1  # Each player assigned to one position

    for position in list(pos_qtd_dict_.keys()):
        prob += lpSum(x[player][position] for player in players) >= 1  # Number of players for each position type

    # Additional constraints for specified numbers of players for each position type
    for position,qtd in pos_qtd_dict_.items():
        prob += lpSum(x[player][position] for player in players) <= qtd 

    # Adding age mean constraint
    if age_constraint:
        total_players = sum(pos_qtd_dict_.values())
        prob += lpSum(ratings.loc[player, "Age"] * x[player][position] for player in players for position in list(pos_qtd_dict_.keys())) / total_players <= age_constraint

    # Total number of players
    prob += lpSum(x[player][position] for player in players for position in list(pos_qtd_dict_.keys())) >= sum(pos_qtd_dict_.values())

    # Solve the problem
    prob.solve()

    # Print the results
    result = []
    for player in players:
        aux={}
        for position in list(pos_qtd_dict_.keys()):
            if value(x[player][position]) == 1:
                aux["name"] = ratings.loc[player, "Name"]
                aux["position"] = position
                aux["score"] = ratings.loc[player, position]
                result.append(aux)
    
    return result, value(prob.objective)

def remove_players(ratings, players):
    return ratings.query("Name not in @players")

def prepare_ratings(ratings, formation):
    return ratings[["Name"] + ["Age"] +list(formation.keys())].fillna(0).reset_index(drop=True)

def treat_transfer_value(df):
    # Remove "£" Symbol
    df["Transfer Value"] = df["Transfer Value"].str.replace("£", "")

    # Split Range Values
    df[["lower_bound", "upper_bound"]] = df["Transfer Value"].str.split(" - ", expand=True)

    # Handle Million (M) Values
    df["lower_bound"] = df["lower_bound"].str.replace("M", "e6")
    df["upper_bound"] = df["upper_bound"].str.replace("M", "e6")

    # Handle Thousand (K) Values
    df["lower_bound"] = df["lower_bound"].str.replace("K", "e3")
    df["upper_bound"] = df["upper_bound"].str.replace("K", "e3")

    # Remove commas and convert to numeric
    df["lower_bound"] = df["lower_bound"].str.replace(",", "")
    df["upper_bound"] = df["upper_bound"].str.replace(",", "")

    df["lower_bound"] = df["lower_bound"].astype(float)
    df["upper_bound"] = df["upper_bound"].astype(float)

    # Convert to Numeric
    df["lower_bound"] = pd.to_numeric(df["lower_bound"])
    df["upper_bound"] = pd.to_numeric(df["upper_bound"])

    # Create a column for mean between upper and lower bounds
    df["mean_value"] = df.apply(lambda row: row["lower_bound"] if pd.isna(row["upper_bound"]) else (row["lower_bound"] + row["upper_bound"]) / 2, axis=1)

    # Display the formatted DataFrame
    return df

def apply_threshold_rule(df, score_column="Highest Role Score", threshold_offset=0.5):
    """
    Applies a threshold rule to numerical columns in a DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame.
        score_column (str): Name of the column containing the score to compute the threshold.
        threshold_offset (float): Offset to subtract from the score column to determine the threshold.

    Returns:
        pd.DataFrame: Transformed DataFrame with values below the threshold set to 0.
    """
    if score_column not in df.columns:
        raise ValueError(f"'{score_column}' column not found in the DataFrame")
    
    # Identify numerical columns (excluding the score column)
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns.difference([score_column])

    # Calculate the threshold
    df['threshold'] = df[score_column] - threshold_offset

    # Apply the threshold rule
    for col in numerical_cols:
        df[col] = df.apply(lambda row: row[col] if row[col] >= row['threshold'] else 0, axis=1)

    # Drop the threshold column before returning (optional)
    df = df.drop(columns=['threshold'])

    return df

def get_best_from_json(json_path, club, formation, players_to_remove=[], age_constraint=None, national_team=False, threshold=0.5):
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    # Extract the "data" part for the DataFrame
    full_squad = pd.DataFrame(json_data["data"])

    if national_team:
        full_squad = full_squad.query("Nat == @club")    
    else:
        full_squad = full_squad.query("Club == @club")
    full_squad = full_squad.query("Name not in @players_to_remove")
    formatted_full_squad = apply_threshold_rule(full_squad, threshold_offset=threshold)
    first_team = pd.DataFrame(get_best(formatted_full_squad, formation, age_constraint)[0])
    second_team = pd.DataFrame(get_best(formatted_full_squad.query("Name not in @first_team.name.tolist()"), formation, age_constraint)[0])
    third_team = pd.DataFrame(get_best(formatted_full_squad.query("Name not in @first_team.name.tolist() and Name not in @second_team.name.tolist()"), formation, age_constraint)[0])
    return first_team, second_team, third_team

def get_players_for_position(json_path, club, formation):
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    # Extract the "data" part for the DataFrame
    full_squad = pd.DataFrame(json_data["data"])

    full_squad = full_squad.query("Club == @club")
    formatted_full_squad = apply_threshold_rule(full_squad)
    result = {}
    for position in formation.keys():
        players_for_position = formatted_full_squad.loc[formatted_full_squad[position] != 0].sort_values(position, ascending=False)
        result[position] = [(name, score) for name, score in players_for_position[["Name", position]].values]
    return result

positions = {'afa': "ST",
 'apa': "M",
 'aps': "M",
 'ad': "",
 'ama': "AM",
 'ams': "AM",
 'bpdc': "D",
 'bpdd': "D",
 'bpds': "D",
 'bwmd': "DM",
 'bwms': "DM",
 'b2bs': "M",
 'cars': "M",
 'cdc': "D",
 'cdd': "D",
 'cds': "D",
 'cma': "M",
 'cmd': "M",
 'cms': "M",
 'cfa': "ST",
 'cfs': "ST",
 'cwba': "WB",
 'cwbs': "WB",
 'dlfa': "ST",
 'dlfs': "ST",
 'dlpd': "M",
 'dlps': "M",
 'dmd': "DM",
 'dms': "DM",
 'dwd': "M",
 'dws': "M",
 'engs': "M",
 'f9s': "AM",
 'fba': "D",
 'fbd': "D",
 'fbs': "D",
 'gkd': "GK",
 'hbd': "DM",
 'ifa': "AM",
 'ifs': "AM",
 'ifbd': "D",
 'iwa': "AM",
 'iws': "AM",
 'iwba': "WB",
 'iwbd': "WB",
 'iwbs': "WB",
 'ld': "D",
 'ls': "D",
 'meza': "M",
 'mezs': "M",
 'ncbc': "",
 'ncbd': "",
 'ncbs': "",
 'nfbd': "",
 'pa': "",
 'pfa': "",
 'pfd': "",
 'pfs': "",
 'raua': "",
 'regs': "",
 'rps': "",
 'sva': "",
 'svs': "",
 'ssa': "",
 'ska': "",
 'skd': "",
 'sks': "",
 'tfa': "",
 'tfs': "",
 'trea': "",
 'wcba': "",
 'wcbd': "",
 'wcbs': "",
 'wma': "",
 'wmd': "",
 'wms': "",
 'wpa': "",
 'wps': "",
 'wtfa': "",
 'wtfs': "",
 'wa': "",
 'ws': "",
 'wba': "",
 'wbd': "",
 'wbs': ""}

positions = ["D", "DM", "M", "AM", "WB", "GK", "ST"]
sides = ["R", "L", "C"]

def extract_positions_sides(pos):
    pos_list = re.findall(r'\b[A-Z]+(?:/[A-Z]+)?\b', pos)  # Extract positions (e.g., "DM", "M", "AM")
    side_list = re.findall(r'\((.*?)\)', pos)  # Extract side info in parentheses (e.g., "RLC")

    pos_dict = {p: int(p in pos_list) for p in positions}
    
    side_flags = "".join(side_list)  # Join side indicators (e.g., "RLC")
    side_dict = {s: int(s in side_flags) for s in sides}
    
    return {**pos_dict, **side_dict}

def parse_transfer_value(value):
    if value.lower() == "not for sale":
        return pd.Series([np.nan, np.nan, np.nan])
    value = value.replace("£", "").replace(",", "")
    
    if " - " in value:
        min_val, max_val = value.split(" - ")
    else:
        min_val = max_val = value
    
    def convert(val):
        if "M" in val:
            return float(val.replace("M", "")) * 1e6
        elif "K" in val:
            return float(val.replace("K", "")) * 1e3
        else:
            return float(val)  # Handle rare cases with no suffix
    
    min_value = convert(min_val)
    max_value = convert(max_val)
    mean_value = (min_value + max_value) / 2
    
    return pd.Series([min_value, max_value, mean_value])

def parse_wage(wage_str):
    """Convert wage strings like '£155,000 p/w' to numeric values."""
    if isinstance(wage_str, str) and "£" in wage_str:
        return float(wage_str.replace("£", "").replace(",", "").replace(" p/w", ""))
    return None  # Handle missing or unexpected values


class ConsoleFormatter:
    """
    Responsible for formatting and printing output to the console.
    This class adheres to the Single Responsibility Principle by handling only presentation.
    """

    def _get_score_color(self, score: int) -> str:
        """
        Returns the appropriate color for a given score.
        """
        if score > 15:
            return Fore.WHITE + Style.BRIGHT  # e.g., Goldenrod-like emphasis
        elif score >= 14:
            return Fore.GREEN
        elif score >= 13:
            return Fore.YELLOW
        elif score >= 10:
            return Fore.LIGHTRED_EX
        else:
            return Fore.LIGHTBLACK_EX

    def print_teams(self, team_df: pd.DataFrame) -> None:
        """
        Prints a formatted team DataFrame with colors and bold text.
        """
        print(Style.BRIGHT + "Team Squads:")
        # Print header with colors and formatting
        print(f"{Fore.CYAN}{Style.BRIGHT}Name{' ' * 10}{Fore.CYAN}{Style.BRIGHT}Position{' ' * 6}{Fore.CYAN}{Style.BRIGHT}Score")
        
        # Iterate through the DataFrame rows
        for _, row in team_df.iterrows():
            name = row['name']
            position = row['position']
            score = row['score']
            score_color = self._get_score_color(score)
            print(f"{Fore.WHITE}{Style.BRIGHT}{name: <20}{position: <10}{score_color}{score}")

    def print_results(self, results_dict: dict) -> None:
        """
        Prints the results in a formatted way with colors and bold text.
        """
        print(Style.BRIGHT + "\nResults by Position:")
        
        for position, players in results_dict.items():
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{position.upper()}:")
            for player, score in players:
                score_color = self._get_score_color(score)
                print(f"  {Fore.WHITE}{Style.BRIGHT}{player: <20}{score_color}{score}")

    def print_formation(self, formation: dict) -> None:
        """
        Prints the squad formation with colors and bold text.
        """
        print(f"{Fore.YELLOW}{Style.BRIGHT}Squad formation:")
        for position, qtd in formation.items():
            print(f"{Fore.GREEN}{Style.BRIGHT}{position.upper()}:")
            print(f"  {Fore.WHITE}{Style.BRIGHT}{qtd}")

from config import BASE_PATH, MONTH_MAP
from pathlib import Path
from datetime import datetime

def get_json_path(team, month="latest", year="latest"):
    path = Path(BASE_PATH) / Path(team)
    json_list = path.glob("*.json")
    file_data = []
    for json_ in json_list:
        json_ = Path(json_)
        stem = json_.stem
        file_month = MONTH_MAP[str(stem)[:-4].lower()]
        file_year = str(stem[-4:])
        try:
            file_year = int(file_year)
        except ValueError:
            continue
        date = datetime(file_year, file_month, 1)
        file_data.append((date, Path(json_)))                                        
        if not file_data:
            raise FileNotFoundError("No valid JSON files found for team: ", team)
        
    if month != "latest":        
        month=month.lower()
        file_data = [(d, f) for d, f in file_data if f.stem.startswith(month)]
        if not file_data:
            raise FileNotFoundError(f"No JSON file found for month '{month}' in team: {team}")

    if year != "latest":        
        try:
            year_int = int(year)
        except ValueError:
            raise ValueError("Year must be a number or 'latest'")
        file_data = [ (d, f) for d, f in file_data if d.year == year_int ]
        if not file_data:
            raise FileNotFoundError(f"No JSON file found for year '{year}' in team: {team}")
    selected_date, selected_file = max(file_data, key=lambda x: x[0])    
    return selected_file

    