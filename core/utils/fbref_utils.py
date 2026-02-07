import re
from typing import Optional, Tuple, Any, Union


def _get_href(cell: Any) -> Optional[str]:
    if not cell:
        return None
    link = cell.find("a")
    return link.get("href") if link else None


def _extract_text(text: str, pattern: Union[str, re.Pattern], idx: int = 1) -> Optional[str]:
    if not text:
        return None
    match = pattern.search(text) if isinstance(pattern, re.Pattern) else re.search(pattern, text)
    if match:
        return match.group(idx)
    return None


def get_text(cell: Any) -> Optional[str]:
    if not cell:
        return None
    text = cell.get_text(strip=True) if hasattr(cell, 'get_text') else str(cell).strip()
    return text if text else None


def get_number(cell: Any) -> Optional[int]:
    text = get_text(cell)
    return int(text) if text and text.isdigit() else None


def get_float(cell: Any) -> Optional[float]:
    text = get_text(cell)
    try:
        return float(text) if text else None
    except ValueError:
        return None


def is_table_header(cell: Any) -> bool:
    return "thead" in cell.get("class", []) if cell else False


def normalize_team_name(name: str) -> Tuple[str, str]:
    parts = name.split()
    ignored_affixes = {"AFC", "FC", "SC", "AC"}

    if parts and parts[0].upper() in ignored_affixes:
        parts = parts[1:]
    if parts and parts[-1].upper() in ignored_affixes:
        parts = parts[:-1]

    clean_name = " ".join(parts)
    return clean_name, "-".join(parts)


REGEX_COMP_CODE = re.compile(r"/en/comps/(Big5|\d+)/")
REGEX_TEAM_CODE = re.compile(r"/en/squads/([a-zA-Z0-9]+)/")
REGEX_MATCH_CODE = re.compile(r"/en/matches/([a-zA-Z0-9]+)")
REGEX_PLAYER_CODE = re.compile(r"/en/players/([a-zA-Z0-9]+)/")
REGEX_COMP_INFO = re.compile(r"/comps/([\w]+)/(\d{4})(?:-\d{4})?/\d{4}(?:-\d{4})?-(.+?)-Stats")


def extract_comp_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_COMP_CODE)


def extract_comp_code_from_cell(cell: Any) -> Optional[str]:
    return extract_comp_code_from_url(_get_href(cell))


def extract_comp_info_from_url(url: str) -> Optional[Tuple[str, int, str]]:
    if not url:
        return None
    match = REGEX_COMP_INFO.search(url)
    if not match:
        return None
    comp_code, season_start, comp_name_slug = match.groups()
    return comp_code, int(season_start), comp_name_slug.replace("-", " ")


def extract_team_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_TEAM_CODE)


def extract_team_code_from_cell(cell: Any) -> Optional[str]:
    return extract_team_code_from_url(_get_href(cell))


def extract_match_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_MATCH_CODE)


def extract_match_code_from_cell(cell: Any) -> Optional[str]:
    return extract_match_code_from_url(_get_href(cell))


def extract_goals_from_cell(cell: Any) -> Optional[int]:
    csk = cell.get("csk") if cell else None
    return int(csk) if csk and csk.strip().isdigit() else None


def extract_venue_epoch(cell: Any) -> Optional[str]:
    if not cell:
        return None
    start_time = cell.find("td", {"data-stat": "start_time"})
    if start_time:
        venue_time = start_time.find("span", {"class": "venuetime"})
        if venue_time:
            return venue_time.get("data-venue-epoch")
    return None


def extract_match_report_url(cell: Any) -> Optional[str]:
    return _get_href(cell)


def extract_player_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_PLAYER_CODE)


def extract_player_code_from_cell(cell: Any) -> Optional[str]:
    return extract_player_code_from_url(_get_href(cell))
