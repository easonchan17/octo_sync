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

# def infer_local_time(
#     venue_date: str,
#     venue_time: str,
#     venue_epoch: str,
#     local_tz_offset:int = 8
# ) -> Optional[datetime]:
#     venue_datetime=combine_date_time(venue_date, venue_time)
#     venue_utc_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)
#     venue_tz_offset = venue_datetime - venue_utc_time.replace(tzinfo=None)

#     venue_datetime_aware = venue_datetime.replace(tzinfo=timezone(venue_tz_offset))
#     local_datetime_aware = venue_datetime_aware.astimezone(timezone(timedelta(hours=local_tz_offset)))
#     return local_datetime_aware

def extract_country_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_country_code_from_url(url)

def extract_country_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/country/([a-zA-Z0-9]+)/")

def extract_comp_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_comp_code_from_url(url)

def extract_comp_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/comps/(Big5|\d+)/")

def extract_club_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_club_code_from_url(url)

def extract_club_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/squads/([a-zA-Z0-9]+)/")

def extract_fixture_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_fixture_code_from_url(url)

def extract_fixture_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/matches/([a-zA-Z0-9]+)")

def extract_player_code_from_cell(cell) -> Optional[str]:
    url = cell.find("a").get("href") if cell and cell.find("a") else None
    return extract_player_code_from_url(url)

def extract_player_code_from_url(url) -> Optional[str]:
    return extract_text(url, r"/en/players/([a-zA-Z0-9]+)/")

def normalize_season_range(season: str) -> str:
    return f"{int(season)}-{int(season)+1}"

def normalize_club_name(name: str) -> tuple[str, str]:
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

def extract_venue_time(cell) -> Optional[str]:
    if not cell:
        return None

    start_time = cell.find("td", {"data-stat": "start_time"})
    if not start_time:
        return None

    venue_time = start_time.find("span", {"class": "venuetime"})
    if not venue_time:
        return None

    return venue_time.get("data-venue-epoch")