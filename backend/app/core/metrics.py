"""Reporting metrics computed from a scheduled task list. Pure functions, no pandas."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Callable, Sequence

from .models import Task
from .working_hours import DEFAULT_CALENDAR, WorkCalendar


def machine_utilization(
    tasks: Sequence[Task], calendar: WorkCalendar = DEFAULT_CALENDAR
) -> dict[str, float]:
    """Average daily utilization per machine (0.0–1.0), averaged across days on which
    the machine had any production. Excludes OutSrc."""
    per_day: dict[tuple[str, date], float] = defaultdict(float)
    for t in tasks:
        if t.machine == "OutSrc" or not t.is_scheduled():
            continue
        assert t.start_time is not None and t.end_time is not None
        current = t.start_time
        while current < t.end_time:
            if current.weekday() not in calendar.weekend_days:
                window_start = max(current, calendar.day_start(current))
                window_end = min(t.end_time, calendar.day_end(current))
                if window_start < window_end:
                    minutes = (window_end - window_start).total_seconds() / 60
                    per_day[(t.machine, window_start.date())] += minutes
            current = (current + timedelta(days=1)).replace(
                hour=calendar.work_start_hour, minute=0, second=0, microsecond=0
            )

    by_machine: dict[str, list[float]] = defaultdict(list)
    for (machine, _day), minutes in per_day.items():
        by_machine[machine].append(minutes / calendar.minutes_per_day)

    return {m: sum(vals) / len(vals) for m, vals in by_machine.items() if vals}


def waiting_time_by(
    tasks: Sequence[Task],
    group_fn: Callable[[Task], str],
    start_fn: Callable[[Task], datetime | None],
    end_fn: Callable[[Task], datetime | None],
    calendar: WorkCalendar = DEFAULT_CALENDAR,
) -> dict[str, float]:
    """Average business-hour wait time (in days, decimal) grouped by `group_fn(task)`."""
    groups: dict[str, list[float]] = defaultdict(list)
    for t in tasks:
        start = start_fn(t)
        end = end_fn(t)
        if start is None or end is None:
            continue
        wait = calendar.business_hours_between(start, end)
        groups[group_fn(t)].append(wait.total_seconds() / (24 * 3600))

    return {g: sum(vs) / len(vs) for g, vs in groups.items() if vs}


def late_products(tasks: Sequence[Task]) -> dict[str, int]:
    """Count of products finishing late vs on-time (by last component's end time)."""
    by_product: dict[str, Task] = {}
    for t in sorted(tasks, key=lambda x: (x.product_name, x.component)):
        if t.is_scheduled():
            by_product[t.product_name] = t

    counts: dict[str, int] = {"late": 0, "on time": 0}
    for t in by_product.values():
        assert t.end_time is not None
        key = "late" if t.end_time > t.promised_delivery_date else "on time"
        counts[key] += 1
    return counts
