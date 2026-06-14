"""Tests for the shared retry helper (S005-006 / ADR-0004 Migration Plan step 2).

The helper consolidates the three previously-duplicate retry loops
(``macro/data_loader.py``, ``yfinance.py``, ``tdx.py``). These tests pin its
contract directly; the sibling adapter batteries
(``test_yfinance_adapter.py``, ``test_tdx_adapter.py``) guard parity for the
delegating call sites.
"""
import pytest

from doge.infrastructure.data_source._retry import fetch_with_retry, is_rate_limited


def test_success_first_call_returns_result_no_retry():
    calls = []

    def fetcher():
        calls.append(1)
        return {"ok": True}

    assert fetch_with_retry(fetcher, max_retries=3, retry_delay=0) == {"ok": True}
    assert len(calls) == 1


def test_retry_then_succeed_returns_data():
    calls = []

    def fetcher():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("transient")
        return "data"

    assert (
        fetch_with_retry(
            fetcher, max_retries=3, retry_delay=0, is_retryable=lambda _: True
        )
        == "data"
    )
    assert len(calls) == 3


def test_exhausted_retries_returns_none():
    calls = []

    def fetcher():
        calls.append(1)
        raise RuntimeError("boom")

    assert (
        fetch_with_retry(
            fetcher, max_retries=3, retry_delay=0, is_retryable=lambda _: True
        )
        is None
    )
    assert len(calls) == 3


def test_non_retryable_raises_immediately():
    calls = []

    def fetcher():
        calls.append(1)
        raise ValueError("genuine bug")

    with pytest.raises(ValueError):
        fetch_with_retry(
            fetcher, max_retries=3, retry_delay=0, is_retryable=lambda _: False
        )
    assert len(calls) == 1


def test_empty_result_treated_as_retryable():
    """None / empty results retry (upstream rate-limits surface as empties)."""
    calls = []

    def fetcher():
        calls.append(1)
        return None

    assert fetch_with_retry(fetcher, max_retries=2, retry_delay=0) is None
    assert len(calls) == 2


def test_empty_list_treated_as_retryable():
    calls = []

    def fetcher():
        calls.append(1)
        return []

    assert fetch_with_retry(fetcher, max_retries=2, retry_delay=0) is None
    assert len(calls) == 2


def test_on_retry_hook_fires_before_each_retry():
    fired = []

    def fetcher():
        if len(fired) < 2:
            raise RuntimeError("transient")
        return "ok"

    def on_retry(attempt, max_retries, exc):
        fired.append((attempt, str(exc)))

    fetch_with_retry(
        fetcher,
        max_retries=3,
        retry_delay=0,
        is_retryable=lambda _: True,
        on_retry=on_retry,
    )
    # First fetch (attempt 0) does not fire on_retry; retries at attempt 1 and 2
    # fire with attempt+1 (2 and 3).
    assert len(fired) == 2
    assert fired[0][0] == 2
    assert fired[1][0] == 3


def test_is_rate_limited_predicate():
    assert is_rate_limited(RuntimeError("Too Many Requests")) is True
    assert is_rate_limited(RuntimeError("HTTP 429 from upstream")) is True
    assert is_rate_limited(RuntimeError("Rate limited")) is True
    assert is_rate_limited(RuntimeError("boom")) is False
    assert is_rate_limited(ValueError("not rate related")) is False
