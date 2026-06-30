# API Reference Entry

The authoritative HTTP API contract remains [../API.md](../API.md).

This page exists to provide a stable lower-case reference path for the new
documentation index while preserving the existing uppercase file that current
tests, CDDs, and ADRs still read directly.

Current contract highlights:

- FastAPI app: `doge.interfaces.api.main:app`
- Default bind: `127.0.0.1:8901`
- Canonical route count: 88 product routes
- Contract test: `tests/contract/test_api_doc_route_coverage.py`
- Error envelope: `{"error": {"code", "message"}}`

Update [../API.md](../API.md) and the contract tests together whenever the live
route set changes.
