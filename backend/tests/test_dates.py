from datetime import date, datetime, timezone

from app.services.dates import local_date, local_midnight_utc, to_utc

import os
import time

import pytest


@pytest.fixture(autouse=True)
def _central_time(monkeypatch):
    """These tests assume US Central time, so pin it here instead of trusting the machine's
    zone. The previous zone is restored afterwards."""
    if not hasattr(time, "tzset"):
        pytest.skip("needs POSIX time zone support")
    monkeypatch.setenv("TZ", "America/Chicago")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()




def test_to_utc_converts_naive_local_wall_clock():
    # America/Chicago in summer is UTC-5 (CDT). 8pm local -> 1am UTC next day.
    naive_local = datetime(2022, 7, 1, 20, 0, 0)
    converted = to_utc(naive_local)
    assert converted == datetime(2022, 7, 2, 1, 0, 0, tzinfo=timezone.utc)


def test_to_utc_handles_dst_correctly_across_seasons():
    # Same wall-clock hour, winter (CST, UTC-6) vs summer (CDT, UTC-5) --
    # the UTC offset must differ, proving this isn't a fixed-offset hack.
    winter = to_utc(datetime(2022, 1, 1, 12, 0, 0))
    summer = to_utc(datetime(2022, 7, 1, 12, 0, 0))
    assert winter.hour == 18  # UTC-6
    assert summer.hour == 17  # UTC-5


def test_to_utc_is_idempotent_on_aware_input():
    aware = datetime(2022, 7, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert to_utc(aware) == aware


def test_local_date_of_naive_utc_near_midnight_boundary():
    # 00:51 UTC on Sep 28 is still 19:51 local (CDT, UTC-5) on Sep 27 --
    # the exact scenario that exposed this bug.
    naive_utc = datetime(2026, 9, 28, 0, 51, 0)
    assert local_date(naive_utc) == date(2026, 9, 27)


def test_local_date_of_aware_utc():
    aware_utc = datetime(2026, 9, 28, 0, 51, 0, tzinfo=timezone.utc)
    assert local_date(aware_utc) == date(2026, 9, 27)


def test_local_midnight_utc_is_inverse_of_local_date():
    d = date(2024, 3, 15)
    assert local_date(local_midnight_utc(d)) == d


def test_local_midnight_utc_differs_by_dst_season():
    winter_midnight = local_midnight_utc(date(2024, 1, 1))
    summer_midnight = local_midnight_utc(date(2024, 7, 1))
    assert winter_midnight.hour == 6  # CST, UTC-6
    assert summer_midnight.hour == 5  # CDT, UTC-5
