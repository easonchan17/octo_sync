import re
from urllib.parse import urlparse
from typing import Optional, Tuple, Any, Union

# ==============================================================================
# 1. Global Regex Patterns
# ==============================================================================
REGEX_COMP_CODE = re.compile(r"/en/comps/(Big5|\d+)/")
REGEX_TEAM_CODE = re.compile(r"/en/squads/([a-zA-Z0-9]+)/")
REGEX_MATCH_CODE = re.compile(r"/en/matches/([a-zA-Z0-9]+)")
REGEX_PLAYER_CODE = re.compile(r"/en/players/([a-zA-Z0-9]+)/")
REGEX_COMP_INFO = re.compile(r"/comps/([\w]+)/(\d{4})(?:-\d{4})?/\d{4}(?:-\d{4})?-(.+?)-Stats")
REGEX_SEASON_RANGE = re.compile(r'^(\d{4})/(\d{4})$')


# ==============================================================================
# 2. Internal Helpers
# ==============================================================================
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


# ==============================================================================
# 3. Basic Utilities (HTML/Text/URL)
# ==============================================================================
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

def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        res = urlparse(url)
        return bool(res.scheme and res.netloc)
    except Exception:
        return False

def normalize_url(url: str) -> str:
    res = urlparse(url)
    return f"{res.scheme}://{res.netloc}{res.path}"


# ==============================================================================
# 4. Domain Extractors (Grouped by Entity)
# ==============================================================================

# --- Competition ---
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


# --- Team ---
def extract_team_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_TEAM_CODE)

def extract_team_code_from_cell(cell: Any) -> Optional[str]:
    return extract_team_code_from_url(_get_href(cell))

def normalize_team_name(name: str) -> Tuple[str, str]:
    parts = name.split()
    ignored_affixes = {"AFC", "FC", "SC", "AC"}

    if parts and parts[0].upper() in ignored_affixes:
        parts = parts[1:]
    if parts and parts[-1].upper() in ignored_affixes:
        parts = parts[:-1]

    clean_name = " ".join(parts)
    return clean_name, "-".join(parts)


# --- Match ---
def extract_match_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_MATCH_CODE)

def extract_match_code_from_cell(cell: Any) -> Optional[str]:
    return extract_match_code_from_url(_get_href(cell))

def parse_scores(scores: str) -> Tuple[Optional[int], Optional[int]]:
    if not scores:
        return None, None
    try:
        parts = scores.split('-')
        if len(parts) == 2:
            return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        pass
    return None, None

def extract_venue_epoch(cell: Any) -> Optional[str]:
    if not cell:
        return None
    start_time = cell.find("td", {"data-stat": "start_time"})
    if start_time:
        venue_time = start_time.find("span", {"class": "venuetime"})
        if venue_time:
            return venue_time.get("data-venue-epoch")
    return None


# --- Player ---
def extract_player_code_from_url(url: str) -> Optional[str]:
    return _extract_text(url, REGEX_PLAYER_CODE)

def extract_player_code_from_cell(cell: Any) -> Optional[str]:
    return extract_player_code_from_url(_get_href(cell))


# --- Season ---
def normalize_season_range(season: int) -> str:
    return f"{season}-{season+1}"

def extract_season_from_range(season_range: str) -> Optional[int]:
    if not season_range:
        return None
    match = REGEX_SEASON_RANGE.match(season_range.strip())
    if match:
        return int(match.group(1))
    return None