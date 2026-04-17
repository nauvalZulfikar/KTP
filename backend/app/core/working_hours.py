from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class WorkCalendar:
    """Defines working hours and weekend days. All scheduler calendar math routes through here."""

    work_start_hour: int = 9
    work_end_hour: int = 17
    weekend_days: frozenset[int] = field(default_factory=lambda: frozenset({5, 6}))

    @property
    def minutes_per_day(self) -> int:
        return (self.work_end_hour - self.work_start_hour) * 60

    def is_weekend(self, dt: datetime) -> bool:
        return dt.weekday() in self.weekend_days

    def next_working_day(self, dt: datetime) -> datetime:
        while self.is_weekend(dt):
            dt += timedelta(days=1)
        return dt

    def day_start(self, dt: datetime) -> datetime:
        return dt.replace(hour=self.work_start_hour, minute=0, second=0, microsecond=0)

    def day_end(self, dt: datetime) -> datetime:
        return dt.replace(hour=self.work_end_hour, minute=0, second=0, microsecond=0)

    def add_working_minutes(self, start: datetime, minutes: float) -> datetime:
        """Advance `start` by `minutes` of working time, skipping non-working hours and weekends."""
        current = start
        remaining = float(minutes)
        while remaining > 0:
            if current.hour < self.work_start_hour or self.is_weekend(current):
                current = self.next_working_day(self.day_start(current))
            elapsed_today = (current.hour - self.work_start_hour) * 60 + current.minute
            available = max(0, self.minutes_per_day - elapsed_today)
            if 0 < remaining <= available:
                current += timedelta(minutes=remaining)
                remaining = 0
            else:
                remaining -= available
                current = self.next_working_day(self.day_start(current) + timedelta(days=1))
        return current

    def business_hours_between(self, start: datetime, end: datetime) -> timedelta:
        """Total working-hour duration between two datetimes, clamped to the work window per day."""
        if end <= start:
            return timedelta()
        total = timedelta()
        current = start
        while current.date() <= end.date():
            if current.weekday() not in self.weekend_days:
                window_start = max(current, self.day_start(current))
                window_end = min(end, self.day_end(current))
                if window_start < window_end:
                    total += window_end - window_start
            current = self.day_start(current) + timedelta(days=1)
        return total


DEFAULT_CALENDAR = WorkCalendar()
