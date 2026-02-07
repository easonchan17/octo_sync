import re
import unicodedata
from typing import Any, Dict, Optional, Tuple
from core.types.enums import MatchStatus

_VALUE_WITH_PERCENT_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)')

def parse_scalar(value: Any, value_type: type) -> Optional[Any]:
    if isinstance(value, str):
        value = value.strip()

    try:
        return value_type(value)
    except (ValueError, TypeError):
        return None

def parse_pair(value: str, value_type1: type, value_type2: type) -> Tuple[Optional[Any], Optional[Any]]:
    if not isinstance(value, str):
        return None, None

    value = value.strip()
    if not value:
        return None, None

    match = _VALUE_WITH_PERCENT_PATTERN.search(value)
    if match is None:
        return None, None

    try:
        return value_type1(match.group(1)), value_type2(match.group(2))
    except (ValueError, TypeError):
        return None, None

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


def extract_status(status: Dict[str, Any]) -> Tuple[int, Optional[str], Optional[int], Optional[int]]:
    if not status:
        return MatchStatus.SCHEDULED.value, None, None, None

    utctime = status.get('utcTime')
    if not utctime:
        return MatchStatus.SCHEDULED.value, None, None, None

    cancelled = status.get('cancelled', False)
    if cancelled:
        return MatchStatus.CANCELLED.value, utctime, None, None

    score_str = status.get('scoreStr')
    home_score, away_score = parse_scores(score_str)

    finished = status.get('finished', False)
    if finished:
        awarded = status.get('awarded', False)
        if awarded:
            return MatchStatus.FINISHED_AWARDED.value, utctime, home_score, away_score
        return MatchStatus.FINISHED.value, utctime, home_score, away_score

    started = status.get('started', False)
    if started:
        return MatchStatus.IN_PROGRESS.value, utctime, home_score, away_score

    return MatchStatus.TIMED.value, utctime, None, None


def extract_season_from_range(season_range: str) -> Optional[int]:
    if not season_range:
        return None
    match = re.match(r'^(\d{4})/(\d{4})$', season_range.strip())
    if match:
        return int(match.group(1))
    return None


class PageUrlBuilder:
    _STOP_WORDS = frozenset({"a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "as", "by"})
    _RE_W_SUFFIX = re.compile(r"-\(w\)|\(w\)")
    _RE_NON_SLUG_CHARS = re.compile(r"[^a-z0-9\s-]")
    _RE_MULTI_HYPHEN = re.compile(r"[\s-]+")
    _CHAR_REPLACEMENTS = {"æ": "ae", "ø": "o", "ß": "ss", "–": "-"}
    _BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"

    @staticmethod
    def _base36_encode(num: int) -> str:
        if num == 0:
            return "0"
        chars = PageUrlBuilder._BASE36_CHARS
        result = []
        while num:
            num, rem = divmod(num, 36)
            result.append(chars[rem])
        return "".join(reversed(result))

    @classmethod
    def _slugify(cls, name: str) -> str:
        if not name:
            return ""

        text = name.lower()
        text = cls._RE_W_SUFFIX.sub("", text)
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        for char, replacement in cls._CHAR_REPLACEMENTS.items():
            if char in text:
                text = text.replace(char, replacement)

        text = cls._RE_NON_SLUG_CHARS.sub("", text)
        text = text.strip()
        text = cls._RE_MULTI_HYPHEN.sub("-", text)

        parts = text.split("-")
        return "-".join([p for p in parts if p and p not in cls._STOP_WORDS])

    @staticmethod
    def _pair_join(a: int, b: int) -> int:
        return (a + b) * (a + b + 1) // 2 + b

    @classmethod
    def build(cls, match_id: int, home_team: Dict[str, Any], away_team: Dict[str, Any]) -> Optional[str]:
        home_id = home_team.get("id")
        away_id = away_team.get("id")
        home_name = home_team.get("longName") or home_team.get("name")
        away_name = away_team.get("longName") or away_team.get("name")

        if not home_id or not away_id or not home_name or not away_name:
            return None

        (id1, name1), (id2, name2) = sorted(
            [(home_id, home_name), (away_id, away_name)],
            key=lambda x: x[0]
        )

        slug = f"{cls._slugify(name1)}-vs-{cls._slugify(name2)}"
        short_code = cls._base36_encode(cls._pair_join(id1, id2))

        return f"/matches/{slug}/{short_code}#{match_id}"