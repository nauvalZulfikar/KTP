from datetime import datetime, timedelta

from app.core.working_hours import WorkCalendar


CAL = WorkCalendar()


def test_minutes_per_day() -> None:
    assert CAL.minutes_per_day == 480


def test_weekend_detection() -> None:
    sat = datetime(2024, 1, 6, 10, 0)  # Saturday
    sun = datetime(2024, 1, 7, 10, 0)
    mon = datetime(2024, 1, 8, 10, 0)
    assert CAL.is_weekend(sat)
    assert CAL.is_weekend(sun)
    assert not CAL.is_weekend(mon)


def test_next_working_day_skips_weekend() -> None:
    sat = datetime(2024, 1, 6, 9, 0)
    assert CAL.next_working_day(sat) == datetime(2024, 1, 8, 9, 0)


def test_add_zero_minutes_returns_same() -> None:
    start = datetime(2024, 1, 8, 10, 0)
    assert CAL.add_working_minutes(start, 0) == start


def test_add_within_single_day() -> None:
    start = datetime(2024, 1, 8, 9, 0)  # Monday 9 AM
    assert CAL.add_working_minutes(start, 60) == datetime(2024, 1, 8, 10, 0)
    assert CAL.add_working_minutes(start, 480) == datetime(2024, 1, 8, 17, 0)


def test_add_rolls_over_to_next_day() -> None:
    start = datetime(2024, 1, 8, 9, 0)
    # 481 min = full 8 hrs + 1 min → next day 9:01
    assert CAL.add_working_minutes(start, 481) == datetime(2024, 1, 9, 9, 1)


def test_add_skips_weekend() -> None:
    fri = datetime(2024, 1, 5, 16, 0)  # Friday 4 PM, 1 hr left in day
    # 120 min = 1 hr today + 1 hr Monday
    assert CAL.add_working_minutes(fri, 120) == datetime(2024, 1, 8, 10, 0)


def test_add_from_before_working_hours_resets() -> None:
    before = datetime(2024, 1, 8, 7, 0)  # Monday 7 AM
    assert CAL.add_working_minutes(before, 60) == datetime(2024, 1, 8, 10, 0)


def test_business_hours_between_same_day() -> None:
    start = datetime(2024, 1, 8, 10, 0)
    end = datetime(2024, 1, 8, 14, 30)
    assert CAL.business_hours_between(start, end) == timedelta(hours=4, minutes=30)


def test_business_hours_between_skips_weekend() -> None:
    fri = datetime(2024, 1, 5, 15, 0)
    mon = datetime(2024, 1, 8, 11, 0)
    # Fri 15:00-17:00 = 2h; Mon 9:00-11:00 = 2h
    assert CAL.business_hours_between(fri, mon) == timedelta(hours=4)


def test_business_hours_between_empty_range() -> None:
    start = datetime(2024, 1, 8, 10, 0)
    assert CAL.business_hours_between(start, start) == timedelta()
    assert CAL.business_hours_between(start, start - timedelta(hours=1)) == timedelta()
