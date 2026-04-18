import sys
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta

class TimelineSegment:
    def __init__(self, start_offset: timedelta, end_offset: timedelta, interval: timedelta) -> None:
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.interval = interval

    def is_active(self, base_time: datetime, current_time: datetime) -> bool:
        start_time = base_time + self.start_offset
        end_time = base_time + self.end_offset
        return start_time <= current_time < end_time

    def suggest_interval(self, base_time: datetime, current_time: datetime) -> timedelta:
        time_to_end = (base_time + self.end_offset) - current_time
        return min(self.interval, max(time_to_end, timedelta(0)))

class TimelineRefetchStrategy:
    def __init__(self, min_interval: timedelta) -> None:
        self._segments: list[TimelineSegment] = []
        self._min_interval = min_interval

    def add_segment(self, start_offset: timedelta, end_offset: Optional[timedelta], interval: timedelta) -> "TimelineRefetchStrategy":
        if end_offset is None:
            end_offset = timedelta(days=36500)

        if interval < self._min_interval:
            raise ValueError(f"Interval {interval} is less than min_interval {self._min_interval}")

        if start_offset >= end_offset:
            raise ValueError(f"Invalid range: start_offset {start_offset} must be less than end_offset {end_offset}")

        if self._segments:
            last_phase = self._segments[-1]
            if start_offset < last_phase.end_offset:
                raise ValueError(f"Sequence violation: start_offset {start_offset} must be >= last end_offset {last_phase.end_offset}")

        self._segments.append(TimelineSegment(start_offset, end_offset, interval))
        return self

    def suggest_interval(self, base_time: datetime, current_time: datetime) -> Optional[timedelta]:
        if not self._segments:
            return None

        first_start_time = base_time + self._segments[0].start_offset
        if current_time < first_start_time:
            return first_start_time - current_time

        for phase in self._segments:
            if phase.is_active(base_time, current_time):
                suggested = phase.suggest_interval(base_time, current_time)
                return max(suggested, self._min_interval)

        return None

class AttemptSegment:
    def __init__(self, min_attempts: int, max_attempts: int, interval: timedelta) -> None:
        self.min_attempts = min_attempts
        self.max_attempts = max_attempts
        self.interval = interval

    def is_active(self, attempts: int) -> bool:
        if attempts < self.min_attempts:
            return False

        if attempts >= self.max_attempts:
            return False

        return True

class AttemptRefetchStrategy:
    def __init__(self) -> None:
        self._segments: list[AttemptSegment] = []

    def add_segment(self, min_attempts: int, max_attempts: Optional[int], interval: timedelta) -> "AttemptRefetchStrategy":
        if max_attempts is None:
            max_attempts = sys.maxsize

        if min_attempts >= max_attempts:
            raise ValueError(f"Invalid range: min_attempts {min_attempts} must be less than max_attempts {max_attempts}")

        if self._segments:
            last = self._segments[-1]
            if last.max_attempts != min_attempts:
                raise ValueError(f"Sequence violation: min_attempts {min_attempts} must equal last max_attempts {last.max_attempts}")

        self._segments.append(AttemptSegment(min_attempts, max_attempts, interval))
        return self

    def suggest_interval(self, attempts: int) -> Optional[timedelta]:
        for segment in self._segments:
            if segment.is_active(attempts):
                return segment.interval

        return None

@dataclass
class ScheduleItem:
    time: datetime
    is_active: bool
class ScheduleRefetchStrategy:
    def __init__(self, active_window: timedelta, active_interval: timedelta) -> None:
        self._active_window = active_window
        self._active_interval = active_interval

    def suggest_interval(self, current_time: datetime, scheduled_items: List[ScheduleItem]) -> Optional[timedelta]:
        if not scheduled_items:
            return None

        window_start = current_time - self._active_window
        sorted_items = sorted(scheduled_items, key=lambda item: item.time)

        for item in sorted_items:
            if item.time < window_start:
                continue

            if item.time > current_time:
                return item.time - current_time

            if item.is_active:
                return self._active_interval

        return None