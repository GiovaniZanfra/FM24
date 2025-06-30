# fm24_selector/cli.py

import argparse

from fm24_selector.config import formations
from fm24_selector.core.json_handler import get_json_path
from fm24_selector.core.selection import get_best_from_json, get_players_for_position
from fm24_selector.formatting import ConsoleFormatter


def parse_args():
    parser = argparse.ArgumentParser(description='FM24 Squad Selector')
    parser.add_argument('-t', '--team', required=True, help='Team to have squad selected')
    parser.add_argument('-r', '--remove', nargs='*', default=[], help='Players to remove')
    parser.add_argument('-f', '--formation', nargs='*',
                        help='Key=Value formation pairs (e.g. ska=1 wba=2)')
    parser.add_argument('--age-constraint', type=int, help='Mean age max')
    parser.add_argument('-d', '--display', type=int, default=1, help='Number of teams to display')
    parser.add_argument('--results', action='store_true', help='Print position results')
    parser.add_argument('--print-formation', action='store_true', help='Print selected formation')
    parser.add_argument('--score-threshold', type=float, default=100, help='Threshold for scores')
    parser.add_argument('--evolution', action='store_true', help='Display player evolution')
    parser.add_argument('--month', default='latest', help='Month to analyze')
    parser.add_argument('--year', default='latest', help='Year to analyze')
    parser.add_argument('--use-positions', action='store_true',
                        help='Zera roles incompatíveis com a posição real do jogador')
    parser.add_argument('--national-squad', action='store_true',
                        help='Coloca a flag national_squad = True')
    return parser.parse_args()


def main():
    args = parse_args()
    formatter = ConsoleFormatter()

    # Monta formation
    if args.formation:
        formation = dict(pair.split('=') for pair in args.formation)
        formation = {k: int(v) for k, v in formation.items()}
    else:
        formation = formations.get(args.team)

    json_path = get_json_path(args.team, args.month, args.year)

    first, second, third = get_best_from_json(
        json_path,
        args.team,
        formation,
        players_to_remove=args.remove,
        age_constraint=args.age_constraint,
        threshold=args.score_threshold,
        use_positions=args.use_positions,
        national_squad=args.national_squad
    )

    results = get_players_for_position(
        json_path,
        args.team,
        formation,
        args.score_threshold,
        use_positions=args.use_positions,
        national_squad=args.national_squad
    )

    if args.print_formation:
        formatter.print_formation(formation)
    if args.results:
        formatter.print_results(results)

    # for team in [first, second, third][: args.display]:
    #     formatter.print_teams(team)

    teams = {"First": first,"Second": second,"Third": third}
    formatter.print_side_by_side(teams, list(formation.keys()))


if __name__ == '__main__':
    main()
