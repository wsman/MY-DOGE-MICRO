"""Docs-consistency gate for docs/API.md (WAVE2-DOC-API).

BLOCKING per ``standards/coding-standards.md`` (Contract story type) and
``.claude/rules/api-code.md`` ("Every endpoint must have contract or integration
tests"). These tests prevent the API reference doc and the live FastAPI app from
drifting on:

1. **Route coverage** — every (method, path) row in the docs/API.md route
   tables must be present in the live ``app.routes`` reported by FastAPI. A
   new route added to the app without a doc row fails the test; a doc row for a
   route that no longer exists also fails.
2. **Error-code table** — the error-contract section of docs/API.md documents
   the SHIPPED S002-009 ``{"error": {"code", "message"}}`` envelope with the
   string-enum codes (``bad_request`` / ``not_found`` / ``conflict`` /
   ``unprocessable`` / ``internal_error``). The table is asserted against the
   real responses returned by representative endpoints (400 / 404 / 409), so
   the doc cannot drift from shipped behavior.

This is a docs-vs-code gate, not a runtime integration test: it parses
docs/API.md for the route table markdown rows and exercises the live app via
``TestClient`` against ``doge.interfaces.api.main:app``. Path-isolation mirrors
``tests/test_api_routers.py:78-83`` (strip sibling-project entries) plus the
``src`` dir on ``sys.path`` so the ``doge`` package imported by the scan router
resolves.
"""
import re
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Path bootstrap — same documented test-shim exception as
# tests/test_api_routers.py:78-83: strip sibling-project (MY-DOGE-PRO) entries.
# The scan router imports `doge.config` (scan.py:26), and `doge` lives under
# `src/`, so `src/` must also be on the path (mirrors pyproject.toml
# [tool.setuptools.packages.find] where=["src"]).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]

from doge.interfaces.api import main as api_main  # noqa: E402

# L-3 product-module marker: this gate covers the full /v1 daemon route surface.
pytestmark = pytest.mark.module_gateway

_ROUTE_TABLE_DOC = _PROJECT_ROOT / "docs" / "reference" / "http-api.md"
_CONTRACTS_DOC = _PROJECT_ROOT / "docs" / "reference" / "http-api-contracts.md"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
# Route table rows look like: | 3 | GET | `/api/scan/servers` | ... |
# or for the top-level helpers: | 1 | GET | `/api/health` | ... |
# We capture the method and the backticked path. The leading index column
# (| N |) makes these rows unambiguous vs prose.
_ROUTE_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*`([^`]+)`",
    re.MULTILINE,
)


def _parse_doc_routes() -> set[tuple[str, str]]:
    """Return the set of (METHOD, path) tuples enumerated in docs/reference/http-api.md."""
    text = _ROUTE_TABLE_DOC.read_text(encoding="utf-8")
    found = set()
    for method, path in _ROUTE_ROW_RE.findall(text):
        found.add((method.upper(), path))
    return found


def _live_routes() -> set[tuple[str, str]]:
    """Return the set of (METHOD, path) tuples the live FastAPI app exposes."""
    out = set()
    for r in api_main.app.routes:
        if isinstance(r, APIRoute):
            for m in r.methods:
                if m in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    out.add((m, r.path))
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """TestClient bound to the live app (with S002-009 handlers wired).

    ``raise_server_exceptions=False`` is REQUIRED to observe the HTTP response
    that ``@app.exception_handler(Exception)`` produces — mirrors
    tests/contract/test_api_error_envelope.py:90.
    """
    return TestClient(api_main.app, raise_server_exceptions=False)


# ===========================================================================
# 1. Route coverage — doc table vs live app.routes
# ===========================================================================
class TestApiDocRouteCoverage:
    def test_doc_route_table_has_expected_row_count(self):
        # Arrange/Act
        doc_routes = _parse_doc_routes()
        # Assert — canonical enumeration: 34 legacy routes + 63 v1/daemon routes.
        assert len(doc_routes) == 97, (
            f"docs/API.md route table should enumerate exactly 97 product "
            f"routes, found {len(doc_routes)}: {sorted(doc_routes)}"
        )

    def test_every_doc_route_exists_in_live_app(self):
        # Arrange
        doc_routes = _parse_doc_routes()
        live = _live_routes()
        # Act — what is in the doc but NOT in the live app?
        missing_from_app = doc_routes - live
        # Assert
        assert not missing_from_app, (
            "docs/API.md enumerates routes that the live FastAPI app does NOT "
            f"expose: {sorted(missing_from_app)}"
        )

    def test_every_live_product_route_is_documented(self):
        # Arrange
        doc_routes = _parse_doc_routes()
        live = _live_routes()
        # Act — strip the OpenAPI infrastructure routes FastAPI adds by default
        # (/docs, /redoc, /openapi.json, /docs/oauth2-redirect); they are
        # documented as infrastructure, not product endpoints.
        infra_paths = {
            "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect",
        }
        live_product = {
            (m, p) for (m, p) in live if p not in infra_paths
        }
        undocumented = live_product - doc_routes
        # Assert
        assert not undocumented, (
            "The live FastAPI app exposes product routes that docs/API.md does "
            f"NOT document: {sorted(undocumented)}"
        )


# ===========================================================================
# 2. Error-code table — docs/API.md error contract vs shipped behavior
# ===========================================================================
class TestApiDocErrorCodeTable:
    """Assert the error-code table in docs/API.md matches shipped responses.

    docs/API.md (Error Contract section) documents:
      - the SHIPPED ``{"error": {"code", "message"}}`` envelope (S002-009);
      - the string-enum ``code`` mapping (bad_request/not_found/conflict/
        unprocessable/internal_error + http_{status} fallback).
    These tests exercise representative endpoints and assert both the envelope
    shape and the exact ``code`` string for the documented status codes, so the
    doc table cannot drift from shipped behavior.
    """

    def test_doc_states_shipped_envelope_not_str_e_leak(self):
        # Arrange — the doc MUST describe the shipped S002-009 envelope, not the
        # pre-S002-009 str(e) leak. (The recon outline flagged the old state;
        # this asserts the doc followed REALITY per the WAVE-2 task rules.)
        text = _CONTRACTS_DOC.read_text(encoding="utf-8")
        # Assert — the stable envelope shape is documented.
        assert '"error": {"code"' in text or '"error": {  "code"' in text, (
            "docs/API.md must document the shipped "
            '{"error": {"code", "message"}} envelope (S002-009).'
        )
        # Assert — the string-enum codes are enumerated.
        for code in (
            "bad_request", "not_found", "conflict",
            "unprocessable", "internal_error",
        ):
            assert code in text, (
                f"docs/API.md error-contract table must list the shipped "
                f"string-enum code '{code}'."
            )
        # Assert — the http_{status} fallback is documented.
        assert "http_{status}" in text or "http_{" in text, (
            "docs/API.md must document the http_{status} fallback code."
        )

    def test_400_returns_bad_request_envelope(self, client):
        # Arrange/Act — POST /api/scan/xx raises HTTPException(400, ...).
        r = client.post("/api/scan/xx", json={})
        # Assert — matches docs/API.md error-code table row for 400.
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "bad_request"
        assert body["error"]["message"] == "market must be 'cn' or 'us'"

    def test_404_returns_not_found_envelope(self, client):
        # Arrange/Act — DELETE a non-existent note raises HTTPException(404).
        r = client.delete("/api/notes/9999999")
        # Assert — matches docs/API.md error-code table row for 404.
        assert r.status_code == 404
        body = r.json()
        assert body["error"]["code"] == "not_found"
        assert body["error"]["message"] == "note not found"

    def test_409_returns_conflict_envelope(self, client):
        # Arrange — deterministically force the scan "already running" path by
        # pre-acquiring the cn scan lock (scan.py:46 _scan_locks). This does NOT
        # edit scan.py source; it only holds the runtime lock so the
        # non-blocking acquire() inside the handler fails -> 409. Released in
        # finally to avoid cross-test bleed (test-standards.md isolation).
        # Mirrors tests/contract/test_api_error_envelope.py:201-214.
        from doge.interfaces.api.routers import scan as scan_router
        lock = scan_router._scan_locks["cn"]
        acquired = lock.acquire(blocking=False)
        assert acquired, "test setup: cn scan lock should be free"
        try:
            # Act
            r = client.post("/api/scan/cn", json={})
            # Assert — matches docs/API.md error-code table row for 409.
            assert r.status_code == 409
            body = r.json()
            assert body["error"]["code"] == "conflict"
            assert body["error"]["message"] == "cn scan already running"
        finally:
            lock.release()
