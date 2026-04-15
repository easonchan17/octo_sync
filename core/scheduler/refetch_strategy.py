from datetime import datetime, timedelta, timezone
from typing import Optional

class RefetchPhase:
    def __init__(self, start_offset: timedelta, end_offset: timedelta, interval: timedelta) -> None:
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.interval = interval

    def is_active(self, kickoff_time: datetime, current_time: datetime) -> bool:
        start_time = kickoff_time + self.start_offset
        end_time = kickoff_time + self.end_offset
        return start_time <= current_time < end_time

    def suggest_interval(self, kickoff_time: datetime, current_time: datetime) -> timedelta:
        time_to_end = (kickoff_time + self.end_offset) - current_time
        return min(self.interval, max(time_to_end, timedelta(0)))

class PhaseRefetchStrategy:
    def __init__(self, min_refetch_interval: timedelta) -> None:
        self._phases: list[RefetchPhase] = []
        self.min_refetch_interval = min_refetch_interval

    def add_phase(self, start_offset: timedelta, end_offset: timedelta, interval: timedelta) -> "PhaseRefetchStrategy":
        if interval < self.min_refetch_interval:
            raise ValueError(f"Interval {interval} is less than min_refetch_interval {self.min_refetch_interval}")

        if start_offset >= end_offset:
            raise ValueError(f"Invalid range: start_offset {start_offset} must be less than end_offset {end_offset}")

        if self._phases:
            last_phase = self._phases[-1]
            if start_offset < last_phase.end_offset:
                raise ValueError(f"Sequence violation: start_offset {start_offset} must be >= last end_offset {last_phase.end_offset}")

        self._phases.append(RefetchPhase(start_offset, end_offset, interval))
        return self

    def suggest_interval(self, kickoff_time: datetime, current_time: datetime) -> Optional[timedelta]:
        if not self._phases:
            return None

        first_start_time = kickoff_time + self._phases[0].start_offset
        if current_time < first_start_time:
            return first_start_time - current_time

        for phase in self._phases:
            if phase.is_active(kickoff_time, current_time):
                suggested = phase.suggest_interval(kickoff_time, current_time)
                return max(suggested, self.min_refetch_interval)

        return None

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
