import re
from typing import Optional, Any
from datetime import datetime, timezone, timedelta

def get_text(cell) -> Optional[str]:
    text = cell.get_text(strip=True) if cell else None
    return text if text else None

def get_number(cell) -> Optional[int]:
    text = get_text(cell)
    return int(text) if text and text.isdigit() else None

def get_float(cell) -> Optional[float]:
    text = get_text(cell)
    try:
        return float(text) if text else None
    except ValueError:
        return None

def extract_number(text: str, pattern: str, idx=1) -> Optional[int]:
    text = extract_text(text, pattern, idx)
    return int(text) if text and text.isdigit() else None

def extract_text(text: str, pattern: str, idx=1) -> Optional[str]:
    if not text:
        return None

    match = re.search(pattern, text)
    if match:
        return match.group(idx)

    return None

def is_table_header(cell) -> bool:
    if not cell:
        return False

    classes = cell.get("class", [])
    return "thead" in classes

def combine_date_time(date_str: str, time_str: str) -> Optional[datetime]:
    if not date_str or not time_str:
        return None

    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

def extract_comp_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_comp_code_from_url(url)

def extract_comp_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/comps/(Big5|\d+)/")

def extract_team_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_team_code_from_url(url)

def extract_team_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/squads/([a-zA-Z0-9]+)/")

def extract_match_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_match_code_from_url(url)

def extract_match_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/matches/([a-zA-Z0-9]+)")

def extract_player_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_player_code_from_url(url)

def extract_player_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/players/([a-zA-Z0-9]+)/")

def extract_season_from_cell(cell) -> Optional[int]:
    text = get_text(cell)
    if not text:
        return None

    if text.isdigit():
        return int(text)

    match = re.match(r'^(\d{4})-\d{4}$', text)
    if match:
        return int(match.group(1))

    return None

def normalize_season_range(season: str) -> str:
    return f"{int(season)}-{int(season)+1}"

def normalize_team_name(name: str) -> tuple[str, str]:
    parts = name.split()

    PREFIX_SUFFIX = {"AFC", "FC", "SC", "AC"}
    if parts and parts[0].upper() in PREFIX_SUFFIX:
        parts = parts[1:]

    if parts and parts[-1].upper() in PREFIX_SUFFIX:
        parts = parts[:-1]

    return (" ".join(parts), "-".join(parts))

def is_match_postponed(cell) -> bool:
    if not cell:
        return False

    return get_text(cell) == "Match Postponed"

def is_match_cancelled(cell) -> bool:
    if not cell:
        return False

    return get_text(cell) == "Match Cancelled"

def is_match_awarded(cell) -> bool:
    if not cell:
        return False

    text = get_text(cell)
    return text.startswith("Match awarded to")

def extract_venue_epoch(cell) -> Optional[str]:
    if not cell:
        return None

    start_time = cell.find("td", {"data-stat": "start_time"})
    if not start_time:
        return None

    venue_time = start_time.find("span", {"class": "venuetime"})
    if not venue_time:
        return None

    return venue_time.get("data-venue-epoch")