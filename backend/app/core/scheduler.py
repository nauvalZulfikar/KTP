"""Greedy production scheduler — pure functions, no framework deps.

Ported from the legacy `scheduler.py`. Behavior is intentionally kept 1:1 with the
original greedy gap-fill algorithm so golden tests can validate the port.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from typing import Iterable, Sequence

from .models import Task
from .working_hours import DEFAULT_CALENDAR, WorkCalendar

MachineSlot = tuple[datetime, datetime, int | None]
MachineSchedule = dict[str, list[MachineSlot]]


def _sort_key(task: Task) -> tuple[datetime, str, str]:
    return (task.promised_delivery_date, task.product_name, task.component)


def find_gaps(machine_schedule: MachineSchedule) -> dict[str, list[tuple[datetime, datetime]]]:
    """Return idle intervals per machine, sorted chronologically."""
    gaps: dict[str, list[tuple[datetime, datetime]]] = {}
    for machine, slots in machine_schedule.items():
        ordered = sorted(slots, key=lambda s: s[0])
        gaps[machine] = []
        for i in range(len(ordered) - 1):
            current_end = ordered[i][1]
            next_start = ordered[i + 1][0]
            if next_start > current_end:
                gaps[machine].append((current_end, next_start))
    return gaps


def _copy_tasks(tasks: Iterable[Task]) -> list[Task]:
    return [replace(t, extras=dict(t.extras)) for t in tasks]


def _product_last_end(data: list[Task], i: int) -> datetime | None:
    product = data[i].product_name
    for t in reversed(data[:i]):
        if t.product_name == product and t.end_time is not None:
            return t.end_time
    return None


def _prev_component_end(data: list[Task], i: int) -> datetime | None:
    task = data[i]
    ends = [
        t.end_time
        for t in data[:i]
        if t.product_name == task.product_name
        and t.component < task.component
        and t.end_time is not None
    ]
    return max(ends) if ends else None


def _schedule_task(
    data: list[Task],
    i: int,
    machine_schedule: MachineSchedule,
    machine_last_end: dict[str, datetime],
    calendar: WorkCalendar,
    previous_schedule: Sequence[Task] | None = None,
) -> None:
    """Assign start_time and end_time to data[i] and update machine state. May append
    a split-remainder task to `data` if the task does not fit a gap."""
    task = data[i]

    same_product_prev = [t for t in data[:i] if t.product_name == task.product_name]
    if same_product_prev:
        product_last_end: datetime = same_product_prev[-1].end_time  # type: ignore[assignment]
    elif previous_schedule is not None:
        prev_ends = [
            t.end_time
            for t in previous_schedule
            if t.product_name == task.product_name
            and t.component < task.component
            and t.end_time is not None
        ]
        product_last_end = max(prev_ends) if prev_ends else task.order_processing_date
    else:
        product_last_end = task.order_processing_date

    gap_start_time: datetime | None = None
    gap_end_time: datetime | None = None

    gaps = find_gaps(machine_schedule)
    for gap_start, gap_end in gaps.get(task.machine, []):
        prev_comp_end = _prev_component_end(data, i)
        effective_prev = prev_comp_end if prev_comp_end is not None else product_last_end

        adjusted_start = max(gap_start, effective_prev)
        if adjusted_start >= gap_end:
            continue

        potential_end = calendar.add_working_minutes(adjusted_start, task.run_time_minutes)

        if potential_end <= gap_end:
            gap_start_time = adjusted_start
            gap_end_time = potential_end
            break

        available_minutes = (gap_end - adjusted_start).total_seconds() / 60
        run_time_min = task.run_time_minutes
        if run_time_min > 0:
            producible_qty = (available_minutes / run_time_min) * task.quantity
        else:
            producible_qty = task.quantity
        to_be_produced = min(producible_qty, task.quantity)
        remaining_qty = task.quantity - to_be_produced

        if remaining_qty > 0:
            remainder = replace(
                task,
                quantity=remaining_qty,
                start_time=None,
                end_time=None,
                extras=dict(task.extras),
            )
            task.quantity = float(int(to_be_produced))
            data.append(remainder)

        gap_start_time = adjusted_start
        gap_end_time = gap_end
        break

    fallback_start: datetime | None = None
    fallback_end: datetime | None = None
    if gap_end_time is None:
        fallback_start = max(product_last_end, machine_last_end[task.machine])
        fallback_end = calendar.add_working_minutes(fallback_start, task.run_time_minutes)

    full_start = max(product_last_end, machine_last_end[task.machine])
    full_end = calendar.add_working_minutes(full_start, task.run_time_minutes)

    start = gap_start_time or fallback_start or full_start
    end = gap_end_time or fallback_end or full_end

    if task.machine != "OutSrc":
        machine_schedule[task.machine].append((start, end, i))
        machine_schedule[task.machine].sort(key=lambda s: s[0])
        machine_last_end[task.machine] = max(machine_last_end[task.machine], end)

    task.start_time = start
    task.end_time = end


def schedule(
    tasks: Sequence[Task],
    calendar: WorkCalendar = DEFAULT_CALENDAR,
) -> list[Task]:
    """Schedule all tasks from scratch. Returns a new list; input is not mutated."""
    data = _copy_tasks(tasks)
    if not data:
        return data

    has_empty = True
    while has_empty:
        min_order_date = min(t.order_processing_date for t in data)
        dummy_time = min_order_date.replace(hour=calendar.work_start_hour, minute=0, second=0, microsecond=0)
        initial_last_end = calendar.next_working_day(dummy_time)

        machines = {t.machine for t in data}
        machine_schedule: MachineSchedule = {m: [(dummy_time, dummy_time, None)] for m in machines}
        machine_last_end = {m: initial_last_end for m in machines}

        i = 0
        while i < len(data):
            data.sort(key=_sort_key)
            task = data[i]

            if "C1" in task.component and task.machine == "OutSrc":
                start = task.order_processing_date.replace(
                    hour=calendar.work_start_hour, minute=0, second=0, microsecond=0
                )
                end = calendar.add_working_minutes(start, task.run_time_minutes)
                task.start_time = start
                task.end_time = end
                i += 1
                continue

            _schedule_task(data, i, machine_schedule, machine_last_end, calendar)
            i += 1

        has_empty = any(not t.is_scheduled() for t in data)

    for t in data:
        t.quantity = float(round(t.quantity))

    return data


def reschedule(
    tasks: Sequence[Task],
    machine_schedule: MachineSchedule,
    machine_last_end: dict[str, datetime],
    previous_schedule: Sequence[Task],
    calendar: WorkCalendar = DEFAULT_CALENDAR,
) -> list[Task]:
    """Schedule tasks that have no start/end time yet, preserving already-scheduled ones
    and the existing machine state. Input is not mutated."""
    data = _copy_tasks(tasks)
    machine_schedule = {m: list(slots) for m, slots in machine_schedule.items()}
    machine_last_end = dict(machine_last_end)
    prev_snapshot = list(previous_schedule)

    has_empty = True
    while has_empty:
        i = 0
        while i < len(data):
            if data[i].is_scheduled():
                i += 1
                continue

            data.sort(key=_sort_key)
            task = data[i]

            if task.machine == "OutSrc":
                prev_comp_end = _prev_component_end(data, i)
                if prev_comp_end is None:
                    prev_comp_end = task.order_processing_date.replace(
                        hour=calendar.work_start_hour, minute=0, second=0, microsecond=0
                    )
                end = calendar.add_working_minutes(prev_comp_end, task.run_time_minutes)
                task.start_time = prev_comp_end
                task.end_time = end
                i += 1
                continue

            _schedule_task(
                data, i, machine_schedule, machine_last_end, calendar, previous_schedule=prev_snapshot
            )
            i += 1

        has_empty = any(not t.is_scheduled() for t in data)

    for t in data:
        t.quantity = float(round(t.quantity))

    return data


def extract_machine_state(
    scheduled_tasks: Sequence[Task],
) -> tuple[MachineSchedule, dict[str, datetime]]:
    """Rebuild machine_schedule and machine_last_end from already-scheduled tasks.
    Mirrors the legacy `extract_machine_state` on a list[Task]."""
    machine_schedule: MachineSchedule = defaultdict(list)
    machine_last_end: dict[str, datetime] = {}
    for idx, t in enumerate(scheduled_tasks):
        if t.start_time is None or t.end_time is None:
            continue
        machine_schedule[t.machine].append((t.start_time, t.end_time, idx))
    for machine, slots in machine_schedule.items():
        slots.sort(key=lambda s: s[0])
        machine_last_end[machine] = max(s[1] for s in slots)
    return dict(machine_schedule), machine_last_end
