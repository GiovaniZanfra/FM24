import pandas as pd
from colorama import Fore, Style


class ConsoleFormatter:
    def _get_score_color(self, score: float) -> str:
        """
        Retorna a cor apropriada para um dado score.
        """
        if score > 15:
            return Fore.WHITE + Style.BRIGHT
        elif score >= 13:
            return Fore.GREEN
        elif score >= 12:
            return Fore.YELLOW
        elif score >= 11:
            return Fore.LIGHTRED_EX
        else:
            return Fore.LIGHTBLACK_EX

    def print_teams(self, team_df: pd.DataFrame) -> None:
        """
        Imprime um DataFrame de time formatado com cores e estilo.
        Espera colunas ['name', 'position', 'score'].
        Comportamento padrão: lista cada jogador em linha separada.
        """
        print(Style.BRIGHT + "Team Squads:")
        header = (
            f"{Fore.CYAN}{Style.BRIGHT}"
            f"{'Name':<20}{'Position':<10}{'Score'}"
        )
        print(header)
        for _, row in team_df.iterrows():
            name = row['name']
            pos = row['position']
            sc = row['score']
            color = self._get_score_color(sc)
            line = (
                f"{Fore.WHITE}{Style.BRIGHT}"
                f"{name:<20}{pos:<10}"
                f"{color}{sc}"
            )
            print(line)

    def print_results(self, results_dict: dict) -> None:
        """
        Imprime os resultados agrupados por posição.
        Espera dict: posição -> list of (player_name, score).
        """
        print(Style.BRIGHT + "\nResults by Position:")
        for position, players in results_dict.items():
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{position.upper()}:")
            for player, sc in players:
                color = self._get_score_color(sc)
                print(f"  {Fore.WHITE}{Style.BRIGHT}{player:<20}{color}{sc}")

    def print_side_by_side(self, teams: dict[str, pd.DataFrame], formation_order: list[str]) -> None:
        """
        Imprime vários DataFrames de equipes lado a lado, na ordem definida por formation_order.
        Espera:
          teams: dict nome_do_time -> DataFrame com ['name', 'position', 'score']
          formation_order: lista de posições na ordem desejada
        Cada linha: Position: TeamA: name score / TeamB: name score / ...
        """
        print(Style.BRIGHT + "Team Squads Side by Side:")
        for position in formation_order:
            segments = []
            for team_name, df in teams.items():
                subset = df[df['position'] == position]
                if subset.empty:
                    continue
                entries = []
                for _, row in subset.iterrows():
                    name, score = row['name'], row['score']
                    color = self._get_score_color(score)
                    entries.append(f"{Fore.WHITE}{Style.BRIGHT}{name} {color}{score}")
                segments.append(
                    f"{Fore.CYAN}{Style.BRIGHT}{team_name}:{Style.RESET_ALL} " + " / ".join(entries)
                )
            if segments:
                line = f" {Fore.YELLOW}/{Style.RESET_ALL} ".join(segments)
                print(f"{Fore.GREEN}{Style.BRIGHT}{position}: {line}")

    def print_formation(self, formation: dict) -> None:
        """
        Imprime o dicionário de formação.
        Espera dict: posição -> quantidade.
        """
        print(f"{Fore.YELLOW}{Style.BRIGHT}Squad formation:")
        for position, qtd in formation.items():
            print(f"{Fore.GREEN}{Style.BRIGHT}{position}: {Fore.WHITE}{Style.BRIGHT}{qtd}")
