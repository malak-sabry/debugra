"""Database timestamp helpers."""

from orchestrator.db import utc_now_naive


def test_utc_now_naive_has_no_timezone():
    assert utc_now_naive().tzinfo is None
