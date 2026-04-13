from typing import Optional
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

def from_timestamp(ts) -> Optional[datetime]:
    return datetime.fromtimestamp(ts, tz=timezone.utc) if ts is not None else None

def begin_time_of_date(
    date_str: str,
    date_fmt: str,
    tz_str: Optional[str] = None
) -> datetime:
    try:
        dt = datetime.strptime(date_str, date_fmt)
        query_date = dt.date()
    except ValueError as e:
        raise ValueError(f"Invalid date '{date_str}' for format '{date_fmt}'") from e

    target_tz = timezone.utc
    if tz_str and tz_str.strip():
        try:
            target_tz = ZoneInfo(tz_str)
        except Exception as e:
            raise ValueError(f"Invalid timezone: '{tz_str}'") from e

    local_start = datetime.combine(query_date, time.min, tzinfo=target_tz)
    return local_start.astimezone(timezone.utc)
