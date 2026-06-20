"""Contract tests for S002-009 — stable, non-leaking API error envelope.

BLOCKING per ``standards/coding-standards.md`` (API Contract story type) and
ADR-0007 Validation criterion (line 317-318): "no response body on any path
contains the raw ``str(e)`` of an internal exception (regression assertion)."

These tests pin two guarantees delivered by the two global exception handlers
registered in ``doge.interfaces.api.main`` (S002-009, ADR-0007 Decision 3):

1. Any otherwise-unhandled ``Exception`` raised inside a router body is caught
   by ``@app.exception_handler(Exception)`` and returned as::

       {"error": {"code": "internal_error", "message": "internal server error"}}

   with HTTP 500. The raw exception message (paths, SQL fragments, type names)
   is logged server-side and MUST NOT appear in the response body.

2. Every ``HTTPException(4xx/5xx, detail)`` is reshaped by
   ``@app.exception_handler(HTTPException)`` into::

       {"error": {"code": <stable-code>, "message": <original detail>}}

   where ``<stable-code>`` is a string enum (``bad_request`` / ``not_found`` /
   ``conflict`` / ``unprocessable`` / ``internal_error``) — not a numeric
   string — so the S002-010 SSE client can branch on ``error.code``.

The previously-leaking sites (six ``except Exception as e: raise HTTPException(
500, str(e))`` wrappers in ``data.py`` and ``notes.py``) are each exercised:
the underlying dependency is monkeypatched to raise
``RuntimeError("boom /secret/path leak")`` and the response is asserted to
carry the stable envelope with NO trace of the secret/path/exception-type.

FastAPI's default 422 ``RequestValidationError`` handler is intentionally left
as-is (out of scope for S002-009) and is NOT enveloped here.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Path bootstrap — same documented test-shim exception as
# tests/test_api_routers.py:78-83: strip sibling-project (MY-DOGE-PRO) entries.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]

from doge.interfaces.api import main as api_main  # noqa: E402
from doge.interfaces.api.routers import scan as scan_router  # noqa: E402
from doge.interfaces.api import deps  # noqa: E402
from doge.core.ports.repository import IStockRepository  # noqa: E402

# A sentinel the global handler must NEVER echo back. It contains an absolute
# path fragment (the real leak shape is a DB path) and the exception class name
# so we can assert neither surfaces.
_LEAK_SENTINEL = "boom /secret/path leak"

_INTERNAL_ENVELOPE = {
    "error": {"code": "internal_error", "message": "internal server error"},
}


def _raise_boom(*_args, **_kwargs):
    """Replacement for any underlying dependency — always raises with the
    sentinel so the no-leak assertion is meaningful."""
    raise RuntimeError(_LEAK_SENTINEL)


@pytest.fixture
def client():
    """A TestClient bound to the live app (with S002-009 handlers wired).

    ``raise_server_exceptions=False`` is REQUIRED to observe the HTTP response
    that a custom ``@app.exception_handler(Exception)`` produces — Starlette's
    TestClient default re-raises the server-side exception in the test process
    (it would otherwise mask the 500 envelope the handler returns). This is the
    documented Starlette idiom for testing exception handlers; it does NOT
    disable the handler.
    """
    return TestClient(api_main.app, raise_server_exceptions=False)


def _assert_internal_envelope(r):
    """Shared assertion for every internal-error path."""
    assert r.status_code == 500, r.text
    assert r.json() == _INTERNAL_ENVELOPE
    # No-leak regression (ADR-0007 line 317-318): the sentinel path and the
    # exception type name MUST NOT appear anywhere in the response.
    assert "secret/path" not in r.text, r.text
    assert "RuntimeError" not in r.text, r.text
    assert _LEAK_SENTINEL not in r.text, r.text


# ===========================================================================
# get_kline internal-error envelope (data.py leak site, removed in S002-009)
# ===========================================================================
class TestKlineInternalErrorEnvelope:
    def test_kline_internal_error_returns_stable_envelope_not_str_e(
        self, client, monkeypatch
    ):
        # Arrange — force the stock repository dependency to raise. The
        # kline handler now receives the repository via Depends(deps.get_stock_repository).
        api_main.app.dependency_overrides[deps.get_stock_repository] = lambda: _raise_boom

        try:
            # Act — valid market + ticker so the handler reaches the repo call.
            r = client.get("/api/data/cn/ticker/000001.SZ/kline?days=10")

            # Assert — stable envelope, no leak.
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}


# ===========================================================================
# notes router internal-error envelopes (5 leak sites, removed in S002-009)
# ===========================================================================
# S007-004: the notes router now receives a ``ManageNotesUseCase`` via
# ``Depends(deps.get_manage_notes_use_case)``. Error injection mirrors the
# kline test above — install a FastAPI dependency override that returns a use
# case whose ``execute`` raises the sentinel, then clear it in ``finally`` so
# the override never leaks into neighbouring tests.
class _RaisingManageNotesUseCase:
    """Stand-in use case whose ``execute`` always raises the leak sentinel."""

    def execute(self, *_a, **_k):
        raise RuntimeError(_LEAK_SENTINEL)


class TestNotesInternalErrorEnvelope:
    def test_get_ticker_context_internal_error_returns_envelope(self, client):
        # Arrange — covers notes.py get_ticker_context leak site.
        api_main.app.dependency_overrides[deps.get_manage_notes_use_case] = (
            lambda: _RaisingManageNotesUseCase()
        )
        try:
            # Act
            r = client.get("/api/notes/ticker/600000.SH")
            # Assert
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}

    def test_add_note_internal_error_returns_envelope(self, client):
        # Arrange — covers notes.py add_note leak site.
        api_main.app.dependency_overrides[deps.get_manage_notes_use_case] = (
            lambda: _RaisingManageNotesUseCase()
        )
        try:
            # Act
            r = client.post(
                "/api/notes", json={"ticker": "600000.SH", "content": "x"}
            )
            # Assert
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}

    def test_search_notes_internal_error_returns_envelope(self, client):
        # Arrange — covers notes.py search_notes leak site.
        api_main.app.dependency_overrides[deps.get_manage_notes_use_case] = (
            lambda: _RaisingManageNotesUseCase()
        )
        try:
            # Act
            r = client.get("/api/notes/search?q=anything")
            # Assert
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}

    def test_recent_notes_internal_error_returns_envelope(self, client):
        # Arrange — covers notes.py recent_notes leak site.
        api_main.app.dependency_overrides[deps.get_manage_notes_use_case] = (
            lambda: _RaisingManageNotesUseCase()
        )
        try:
            # Act
            r = client.get("/api/notes/recent")
            # Assert
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}

    def test_tracked_tickers_internal_error_returns_envelope(self, client):
        # Arrange — covers notes.py tracked_tickers leak site.
        api_main.app.dependency_overrides[deps.get_manage_notes_use_case] = (
            lambda: _RaisingManageNotesUseCase()
        )
        try:
            # Act
            r = client.get("/api/notes/tracked")
            # Assert
            _assert_internal_envelope(r)
        finally:
            api_main.app.dependency_overrides = {}


# ===========================================================================
# HTTPException envelope shape (400 / 404 / 409) — the second global handler
# ===========================================================================
class TestHttpExceptionEnvelope:
    def test_400_bad_request_envelope_preserves_detail(self, client):
        # Arrange/Act — POST /api/scan/xx raises HTTPException(400, ...).
        r = client.post("/api/scan/xx", json={})
        # Assert — stable code enum + original operator-safe detail.
        assert r.status_code == 400
        assert r.json() == {
            "error": {"code": "bad_request",
                      "message": "market must be 'cn' or 'us'"}
        }

    def test_404_not_found_envelope_preserves_detail(self, client):
        # Arrange/Act — DELETE a non-existent note raises HTTPException(404).
        r = client.delete("/api/notes/9999999")
        # Assert
        assert r.status_code == 404
        assert r.json() == {
            "error": {"code": "not_found", "message": "note not found"}
        }

    def test_409_conflict_envelope_preserves_detail(self, client):
        # Arrange — deterministically force the scan "already running" path by
        # pre-acquiring the cn scan lock (scan.py:131 _scan_locks). This does
        # NOT edit scan.py source; it only holds the runtime lock so the
        # non-blocking acquire() inside the handler fails -> 409. Released in
        # finally to avoid cross-test bleed (test-standards.md isolation).
        lock = scan_router._scan_locks["cn"]
        acquired = lock.acquire(blocking=False)
        assert acquired, "test setup: cn scan lock should be free"
        try:
            # Act
            r = client.post("/api/scan/cn", json={})
            # Assert
            assert r.status_code == 409
            assert r.json() == {
                "error": {"code": "conflict",
                          "message": "cn scan already running"}
            }
        finally:
            lock.release()
