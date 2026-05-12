import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from core.types.enums import MatchStatus


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


def extract_status(status: Dict[str, Any], time_window: timedelta) -> Tuple[int, Optional[str], Optional[int], Optional[int]]:
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

    post_match_duration = datetime.now(timezone.utc) - datetime.fromisoformat(utctime)
    if post_match_duration.total_seconds() > time_window.total_seconds():
        first_half_started = status.get('halfs', {}).get('firstHalfStarted')
        if first_half_started is not None:
            return MatchStatus.FINISHED.value, utctime, home_score, away_score

    return MatchStatus.TIMED.value, utctime, None, None


def encode_id(raw_id: int, salt: str) -> str:
    raw = f"{salt}:{raw_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]