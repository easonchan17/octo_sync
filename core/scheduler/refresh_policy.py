from datetime import date, datetime, timedelta, timezone
from typing import Optional, Set


class FixtureRefreshPolicy:
    def __init__(self, fast_interval_minutes: float, slow_interval_minutes: float) -> None:
        self.fast_interval = timedelta(minutes=fast_interval_minutes)
        self.slow_interval = timedelta(minutes=slow_interval_minutes)

    def set_avtive_dates(self, active_dates: Set[date]) -> None:
        self.active_dates = active_dates

    def can_fetch(self, match_date: date, last_fetched_at: Optional[datetime]) -> bool:
        if not last_fetched_at:
            return True
        interval = self.fast_interval if match_date in self.active_dates else self.slow_interval
        return last_fetched_at + interval <= datetime.now(timezone.utc)


class MatchRefreshPolicy:
    def __init__(self, start_offset_hours: Optional[float], end_offset_hours: Optional[float], refresh_interval_minutes: Optional[float] = None, min_priority: int = 0) -> None:
        assert start_offset_hours is not None or end_offset_hours is not None, "At least one of start_offset_hours or end_offset_hours must be provided"

        self.start_offset = timedelta(hours=start_offset_hours) if start_offset_hours is not None else None
        self.end_offset = timedelta(hours=end_offset_hours) if end_offset_hours is not None else None
        self.refresh_interval = timedelta(minutes=refresh_interval_minutes) if refresh_interval_minutes is not None else None
        self.min_priority = min_priority

    def is_active(self, kickoff_time: datetime) -> bool:
        now = datetime.now(timezone.utc)

        if self.start_offset is not None and now < kickoff_time + self.start_offset:
            return False

        if self.end_offset is not None and now >= kickoff_time + self.end_offset:
            return False

        return True

    def can_fetch(self, kickoff_time: datetime, last_fetched_time: Optional[datetime], priority: int = 0) -> bool:
        if priority < self.min_priority:
            return False

        if not last_fetched_time:
            return True

        if self.refresh_interval:
            return last_fetched_time + self.refresh_interval <= datetime.now(timezone.utc)
        else:
            return self.start_offset is not None and last_fetched_time < kickoff_time + self.start_offset


class OddsRefreshPolicy:
    def __init__(self, start_offset_minutes: Optional[float], end_offset_minutes: Optional[float], refresh_interval_minutes: float) -> None:
        assert start_offset_minutes is not None or end_offset_minutes is not None, "At least one of start_offset_minutes or end_offset_minutes must be provided"

        self.start_offset = timedelta(minutes=start_offset_minutes) if start_offset_minutes is not None else None
        self.end_offset = timedelta(minutes=end_offset_minutes) if end_offset_minutes is not None else None
        self.refresh_interval = timedelta(minutes=refresh_interval_minutes)

    def is_active(self, kickoff_time: datetime, current_time: datetime) -> bool:
        if self.start_offset is not None and current_time < kickoff_time + self.start_offset:
            return False

        if self.end_offset is not None and current_time >= kickoff_time + self.end_offset:
            return False

        return True

    def suggested_interval(self, kickoff_time: datetime, current_time: datetime) -> timedelta:
        if self.end_offset is None:
            return self.refresh_interval

        time_to_next_stage = (kickoff_time + self.end_offset) - current_time
        return min(self.refresh_interval, max(time_to_next_stage, timedelta(0)))

class MappingRefreshPolicy:
    def __init__(self, min_attempts: Optional[int], max_attempts: Optional[int], refresh_interval_minutes: float) -> None:
        self.min_attempts = min_attempts
        self.max_attempts = max_attempts
        self.refresh_interval = timedelta(minutes=refresh_interval_minutes)

    def is_active(self, attempts: int) -> bool:
        if self.min_attempts is not None and attempts < self.min_attempts:
            return False

        if self.max_attempts is not None and attempts >= self.max_attempts:
            return False

        return True
