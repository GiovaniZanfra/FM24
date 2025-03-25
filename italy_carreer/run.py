# coding: utf-8
import argparse
from utils import get_best_from_json, get_players_for_position
from config import formations
import pandas as pd
from utils import ConsoleFormatter, get_json_path

parser = argparse.ArgumentParser(description='FM24 Squad Selector')
parser.add_argument('--team', '-t', type=str, help='Team to have squad selected')
parser.add_argument('--remove', '-r', default=[], type=str, nargs='*', help='List of players to remove')
parser.add_argument('--formation', '-f', default=None, nargs='*',
                    help='Formation to select squad. Pass in key-value pairs')
parser.add_argument('--age-constraint', default=None, type=int,
                    help='Mean Age constraint when selecting squad')
parser.add_argument('--display', '-d', default=1, type=int, help="Number of teams to display")
parser.add_argument('--results', default=True, type=bool, help="Prints positions results.")
parser.add_argument('--print-formation', default=False, type=bool, help="If user wants to print the formation that gets selected.")
parser.add_argument('--score-threshold', default=0.5, type=float, help="Value to apply on threshold rule")
parser.add_argument('--evolution', default=False, type=bool, help="if you want to display plaryer evolution (default:False)")
parser.add_argument('--month', default="latest", type=str, help="month you're trying to analyze")
parser.add_argument('--year', default="latest", help="year you're trying to analyze")


args = parser.parse_args()
formatter = ConsoleFormatter()

def main():
    if args.formation is not None:
        args.formation = dict(pair.split('=') for pair in args.formation)
        args.formation = {k:int(v) for k, v in args.formation.items()}
    if (args.formation is None) and (args.team in formations.keys()):
        args.formation = formations[args.team]
    json_path = get_json_path(args.team, args.month, args.year)
    first_team, second_team, third_team = get_best_from_json(json_path, args.team, args.formation, players_to_remove=args.remove, age_constraint=args.age_constraint, threshold=args.score_threshold)
    result = get_players_for_position(json_path, args.team, args.formation)
    best_teams = [first_team, second_team, third_team]
    if args.print_formation:
        formatter.print_formation(args.formation)

    if args.results:
       formatter.print_results(result)

    for i in range(args.display):
       team = best_teams[i]
       formatter.print_teams(team)

    
if __name__ == '__main__':
  main()