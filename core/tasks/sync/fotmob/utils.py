import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from core.types.enums import MatchStatus


def parse_finish_time(halfs: Optional[Dict], kickoff_str_utc: Optional[str], kickoff_str_local: Optional[str]) -> Optional[datetime]:
    if not halfs or not kickoff_str_utc or not kickoff_str_local:
        return None

    game_ended_str_local = halfs.get("gameEnded")
    if not game_ended_str_local:
        return None

    try:
        kickoff_utc = datetime.fromisoformat(kickoff_str_utc)
        kickoff_local = datetime.strptime(kickoff_str_local, "%d.%m.%Y %H:%M")
        utc_offset = kickoff_local - kickoff_utc.replace(tzinfo=None)
        game_ended_local = datetime.strptime(game_ended_str_local, "%d.%m.%Y %H:%M:%S")
        return (game_ended_local - utc_offset).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


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


def extract_status(status: Dict[str, Any]) -> Tuple[int, Optional[str], Optional[int], Optional[int], Optional[Dict], Optional[Dict]]:
    if not status:
        return MatchStatus.SCHEDULED.value, None, None, None, None, None

    utctime = status.get('utcTime')
    if not utctime:
        return MatchStatus.SCHEDULED.value, None, None, None, None, None

    halfs_status = status.get('halfs')
    live_status = status.get('liveTime')

    cancelled = status.get('cancelled', False)
    if cancelled:
        return MatchStatus.CANCELLED.value, utctime, None, None, None, None

    score_str = status.get('scoreStr')
    home_score, away_score = parse_scores(score_str)

    finished = status.get('finished', False)
    if finished:
        awarded = status.get('awarded', False)
        if awarded:
            return MatchStatus.FINISHED_AWARDED.value, utctime, home_score, away_score, halfs_status, live_status
        return MatchStatus.FINISHED.value, utctime, home_score, away_score, halfs_status, live_status

    started = status.get('started', False)
    if started:
        return MatchStatus.IN_PROGRESS.value, utctime, home_score, away_score, halfs_status, live_status

    if home_score is not None:
        if live_status is not None:
            return MatchStatus.IN_PROGRESS.value, utctime, home_score, away_score, halfs_status, live_status
        return MatchStatus.FINISHED.value, utctime, home_score, away_score, halfs_status, live_status

    return MatchStatus.TIMED.value, utctime, None, None, None, None


def encode_id(raw_id: int, salt: str) -> str:
    raw = f"{salt}:{raw_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
