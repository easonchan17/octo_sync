from ast import pattern
from typing import List, Any
import re
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.player_match_stats import PlayerMatchStats
from core.utils.html_utils import (
    get_number, get_float, get_text,
    is_table_header,
    extract_player_code_from_cell
)

class PlayerMatchStatsReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[PlayerMatchStats]:
        soup = BeautifulSoup(page_content, 'html.parser')

        player_stats_dict = {}

        summary_pattern = re.compile(r"^stats_([a-zA-Z0-9]{8})_summary$")
        summary_tables = soup.find_all("table", id=summary_pattern)
        for stats_table in summary_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            table_id = stats_table['id']
            match = summary_pattern.search(table_id)
            team_code = match.group(1)
            rows = table_body.find_all("tr")

            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)
                if player_code not in player_stats_dict:
                    player_stats_dict[player_code] = {}

                position = row.find("td", {"data-stat": "position"})
                minutes = row.find("td", {"data-stat": "minutes"})
                goals = row.find("td", {"data-stat": "goals"})
                shots = row.find("td", {"data-stat": "shots"})
                shots_on_target = row.find("td", {"data-stat": "shots_on_target"})
                npxg = row.find("td", {"data-stat": "npxg"})
                xg_assist = row.find("td", {"data-stat": "xg_assist"})
                shot_creating_actions = row.find("td", {"data-stat": "sca"})
                tackles = row.find("td", {"data-stat": "tackles"})
                interceptions = row.find("td", {"data-stat": "interceptions"})
                blocks = row.find("td", {"data-stat": "blocks"})

                player_stats_dict[player_code].update({
                    "team_code": team_code,
                    "player_name": player.text,
                    "is_starter": True if re.match(r'^\S', player.text) else False,
                    "player_code": player_code,
                    "position": get_text(position),
                    "minutes": get_number(minutes),
                    "goals": get_number(goals),
                    "shots": get_number(shots),
                    "shots_on_target": get_number(shots_on_target),
                    "npxg": get_float(npxg),
                    "xg_assist": get_float(xg_assist),
                    "shot_creating_actions": get_number(shot_creating_actions),
                    "tackles": get_number(tackles),
                    "interceptions": get_number(interceptions),
                    "blocks": get_number(blocks)
                })

        passing_tables = soup.find_all("table", id=re.compile(r"^stats_[a-zA-Z0-9]{8}_passing$"))
        for stats_table in passing_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)

                progressive_passes = row.find("td", {"data-stat": "progressive_passes"})
                assisted_shots = row.find("td", {"data-stat": "assisted_shots"})

                player_stats_dict[player_code].update({
                    "progressive_passes": get_number(progressive_passes),
                    "key_passes": get_number(assisted_shots)
                })

        possession_tables = soup.find_all("table", id=re.compile(r"^stats_[a-zA-Z0-9]{8}_possession$"))
        for stats_table in possession_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)

                progressive_carries = row.find("td", {"data-stat": "progressive_carries"})
                take_ons_won = row.find("td", {"data-stat": "take_ons_won"})
                dispossessed = row.find("td", {"data-stat": "dispossessed"})
                miscontrols = row.find("td", {"data-stat": "miscontrols"})

                player_stats_dict[player_code].update({
                    "progressive_carries": get_number(progressive_carries),
                    "take_ons_won": get_number(take_ons_won),
                    "dispossessed": get_number(dispossessed),
                    "miscontrols": get_number(miscontrols)
                })

        defense_tables = soup.find_all("table", id=re.compile(r"^stats_[a-zA-Z0-9]{8}_defense$"))
        for stats_table in defense_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)

                tackles_won = row.find("td", {"data-stat": "tackles_won"})
                challenges_lost = row.find("td", {"data-stat": "challenges_lost"})

                player_stats_dict[player_code].update({
                    "tackles_won": get_number(tackles_won),
                    "challenges_lost": get_number(challenges_lost)
                })

        misc_tables = soup.find_all("table", id=re.compile(r"^stats_[a-zA-Z0-9]{8}_misc$"))
        for stats_table in misc_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)

                fouled = row.find("td", {"data-stat": "fouled"})
                ball_recoveries = row.find("td", {"data-stat": "ball_recoveries"})
                aerials_won = row.find("td", {"data-stat": "aerials_won"})
                aerials_lost = row.find("td", {"data-stat": "aerials_lost"})

                player_stats_dict[player_code].update({
                    "fouls_drawn": get_number(fouled),
                    "ball_recoveries": get_number(ball_recoveries),
                    "aerials_won": get_number(aerials_won),
                    "aerials_lost": get_number(aerials_lost)
                })

        keeper_tables = soup.find_all("table", id=re.compile(r"^keeper_stats_[a-zA-Z0-9]{8}$"))
        for stats_table in keeper_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                player = row.find("th", {"data-stat": "player"})
                player_code = extract_player_code_from_cell(player)

                gk_goals_against = row.find("td", {"data-stat": "gk_goals_against"})
                gk_psxg = row.find("td", {"data-stat": "gk_psxg"})
                gk_crosses = row.find("td", {"data-stat": "gk_crosses"})
                gk_crosses_stopped = row.find("td", {"data-stat": "gk_crosses_stopped"})
                gk_def_actions_outside_pen_area = row.find("td", {"data-stat": "gk_def_actions_outside_pen_area"})

                player_stats_dict[player_code].update({
                    "gk_goals_against": get_number(gk_goals_against),
                    "gk_psxg": get_float(gk_psxg),
                    "gk_crosses": get_number(gk_crosses),
                    "gk_crosses_stopped": get_number(gk_crosses_stopped),
                    "gk_def_actions_outside_pen_area": get_number(gk_def_actions_outside_pen_area)
                })

        player_stats = []
        for player_code, stats in player_stats_dict.items():
            player_stat = PlayerMatchStats(
                match_code=None,
                player_code=player_code,
                team_code=stats.get("team_code"),
                player_name=stats.get("player_name"),
                position=stats.get("position"),
                minutes=stats.get("minutes"),
                is_starter=stats.get("is_starter"),
                goals=stats.get("goals"),
                shots=stats.get("shots"),
                shots_on_target=stats.get("shots_on_target"),
                npxg=stats.get("npxg"),
                xg_assist=stats.get("xg_assist"),
                shot_creating_actions=stats.get("shot_creating_actions"),
                tackles=stats.get("tackles"),
                tackles_won=stats.get("tackles_won"),
                blocks=stats.get("blocks"),
                interceptions=stats.get("interceptions"),
                progressive_passes=stats.get("progressive_passes"),
                key_passes=stats.get("key_passes"),
                progressive_carries=stats.get("progressive_carries"),
                take_ons_won=stats.get("take_ons_won"),
                dispossessed=stats.get("dispossessed"),
                miscontrols=stats.get("miscontrols"),
                fouls_drawn=stats.get("fouls_drawn"),
                ball_recoveries=stats.get("ball_recoveries"),
                aerials_won=stats.get("aerials_won"),
                aerials_lost=stats.get("aerials_lost"),
                challenges_lost=stats.get("challenges_lost"),
                gk_goals_against=stats.get("gk_goals_against"),
                gk_psxg=stats.get("gk_psxg"),
                gk_crosses=stats.get("gk_crosses"),
                gk_crosses_stopped=stats.get("gk_crosses_stopped"),
                gk_def_actions_outside_pen_area=stats.get("gk_def_actions_outside_pen_area")
            )
            player_stats.append(player_stat)

        return player_stats
