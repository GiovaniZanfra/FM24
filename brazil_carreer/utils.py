from typing import Optional
import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value
import json
import logging
from functools import wraps

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

def get_best_from_json(json_path, club, formation, players_to_remove=[], age_constraint=None):
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    # Extract the "data" part for the DataFrame
    full_squad = pd.DataFrame(json_data["data"])

    full_squad = full_squad.query("Club == @club")
    full_squad = full_squad.query("Name not in @players_to_remove")
    formatted_full_squad = apply_threshold_rule(full_squad)
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