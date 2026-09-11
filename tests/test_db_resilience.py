"""
Tests for the startup database-readiness gate.

Covers ``wait_for_database`` - the retry/backoff loop that keeps the
container from crash-looping when Postgres isn't ready yet on a cold boot
(BA-13 / HANDOFF.md's recurring post-reboot I/O-storm race). Mirrors
baselayer's test_db_resilience.py (commit 8bf204d).
"""

import pytest

from app import database


@pytest.mark.asyncio
async def test_wait_for_database_retries_then_succeeds(monkeypatch):
    """Transient connect failures are retried; the loop returns once one succeeds."""
    calls = {"n": 0}

    async def flaky_check():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("connection refused")

    slept: list[float] = []

    async def fake_sleep(delay):
        slept.append(delay)

    monkeypatch.setattr(database, "_check_database_connection", flaky_check)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    await database.wait_for_database(max_attempts=5, base_delay=1.0, max_delay=10.0)

    assert calls["n"] == 3
    assert slept == [1.0, 2.0]


@pytest.mark.asyncio
async def test_wait_for_database_backoff_is_capped(monkeypatch):
    """Delay grows exponentially but never exceeds max_delay."""
    calls = {"n": 0}

    async def flaky_check():
        calls["n"] += 1
        if calls["n"] < 6:
            raise OSError("not ready")

    slept: list[float] = []

    async def fake_sleep(delay):
        slept.append(delay)

    monkeypatch.setattr(database, "_check_database_connection", flaky_check)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    await database.wait_for_database(max_attempts=10, base_delay=1.0, max_delay=5.0)

    assert slept == [1.0, 2.0, 4.0, 5.0, 5.0]
    assert max(slept) == 5.0


@pytest.mark.asyncio
async def test_wait_for_database_gives_up_and_raises(monkeypatch):
    """After max_attempts the loop raises, chaining the last real error."""

    async def always_fail():
        raise OSError("host unreachable")

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(database, "_check_database_connection", always_fail)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="not reachable after 4 attempts") as exc_info:
        await database.wait_for_database(max_attempts=4, base_delay=0.01, max_delay=0.02)

    assert isinstance(exc_info.value.__cause__, OSError)


@pytest.mark.asyncio
async def test_wait_for_database_succeeds_first_try_without_sleeping(monkeypatch):
    """Happy path: one successful check, no backoff sleep at all."""

    async def ok_check():
        return None

    slept: list[float] = []

    async def fake_sleep(delay):
        slept.append(delay)

    monkeypatch.setattr(database, "_check_database_connection", ok_check)
    monkeypatch.setattr(database.asyncio, "sleep", fake_sleep)

    await database.wait_for_database(max_attempts=3)

    assert slept == []


@pytest.mark.asyncio
async def test_wait_for_database_against_real_sqlite_engine():
    """Sanity check against the real (test) engine, no monkeypatching: the
    happy path actually opens a connection and runs SELECT 1 against
    whatever ``database.engine`` currently is (conftest's sqlite override)."""
    await database.wait_for_database(max_attempts=1)
