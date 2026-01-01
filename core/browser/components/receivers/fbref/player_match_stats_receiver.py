import re
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.player_match_stats import PlayerMatchStats
from core.utils.parsing import (
    get_number, get_float, get_text,
    is_table_header,
    extract_player_code_from_cell,
    extract_match_code_from_url
)

class PlayerMatchStatsReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        match_code = extract_match_code_from_url(url)
        if not match_code:
            raise ValueError(f"Match code not found in the URL: {url}")

        soup = BeautifulSoup(page_content, 'html.parser')

        player_stats_dict = {}

        summary_pattern = re.compile(r"^stats_([a-zA-Z0-9]{8})_summary$")
        summary_tables = soup.find_all("table", id=summary_pattern)
        for stats_table in summary_tables:
            table_body = stats_table.find("tbody")
            if not table_body:
                raise ValueError("Table body not found")

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
                pens_made = row.find("td", {"data-stat": "pens_made"})
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
                    "penalties_made": get_number(pens_made),
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
                raise ValueError("Table body not found")

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
                raise ValueError("Table body not found")

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
                raise ValueError("Table body not found")

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
                raise ValueError("Table body not found")

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
                raise ValueError("Table body not found")

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
            player_stat = {
                PlayerMatchStats.match_code.key: match_code,
                PlayerMatchStats.player_code.key: player_code,
                PlayerMatchStats.team_code.key: stats.get("team_code"),
                PlayerMatchStats.player_name.key: stats.get("player_name"),
                PlayerMatchStats.position.key: stats.get("position"),
                PlayerMatchStats.minutes.key: stats.get("minutes"),
                PlayerMatchStats.is_starter.key: stats.get("is_starter"),
                PlayerMatchStats.goals.key: stats.get("goals"),
                PlayerMatchStats.penalties_made.key: stats.get("penalties_made"),
                PlayerMatchStats.shots.key: stats.get("shots"),
                PlayerMatchStats.shots_on_target.key: stats.get("shots_on_target"),
                PlayerMatchStats.npxg.key: stats.get("npxg"),
                PlayerMatchStats.xg_assist.key: stats.get("xg_assist"),
                PlayerMatchStats.shot_creating_actions.key: stats.get("shot_creating_actions"),
                PlayerMatchStats.tackles.key: stats.get("tackles"),
                PlayerMatchStats.tackles_won.key: stats.get("tackles_won"),
                PlayerMatchStats.blocks.key: stats.get("blocks"),
                PlayerMatchStats.interceptions.key: stats.get("interceptions"),
                PlayerMatchStats.progressive_passes.key: stats.get("progressive_passes"),
                PlayerMatchStats.key_passes.key: stats.get("key_passes"),
                PlayerMatchStats.progressive_carries.key: stats.get("progressive_carries"),
                PlayerMatchStats.take_ons_won.key: stats.get("take_ons_won"),
                PlayerMatchStats.dispossessed.key: stats.get("dispossessed"),
                PlayerMatchStats.miscontrols.key: stats.get("miscontrols"),
                PlayerMatchStats.fouls_drawn.key: stats.get("fouls_drawn"),
                PlayerMatchStats.ball_recoveries.key: stats.get("ball_recoveries"),
                PlayerMatchStats.aerials_won.key: stats.get("aerials_won"),
                PlayerMatchStats.aerials_lost.key: stats.get("aerials_lost"),
                PlayerMatchStats.challenges_lost.key: stats.get("challenges_lost"),
                PlayerMatchStats.gk_goals_against.key: stats.get("gk_goals_against"),
                PlayerMatchStats.gk_psxg.key: stats.get("gk_psxg"),
                PlayerMatchStats.gk_crosses.key: stats.get("gk_crosses"),
                PlayerMatchStats.gk_crosses_stopped.key: stats.get("gk_crosses_stopped"),
                PlayerMatchStats.gk_def_actions_outside_pen_area.key: stats.get("gk_def_actions_outside_pen_area")
            }
            player_stats.append(player_stat)

        return player_stats
