# API Reference Entry

The authoritative HTTP API route table and per-route reference live in
[http-api.md](http-api.md). The reader quick guide is [../API.md](../API.md);
transport, SSE, CORS, error, concurrency, and OpenAPI contracts are in
[http-api-contracts.md](http-api-contracts.md).

This lower-case alias keeps the stable `docs/reference/api.md` path available
for the documentation index and existing links. It must stay small and must not
duplicate the route table.

Current contract highlights:

- FastAPI app: `doge.interfaces.api.main:app`
- Default bind: `127.0.0.1:8901`
- Canonical route count: 98 HTTP routes
- Contract test: `tests/contract/test_api_doc_route_coverage.py`
- Error envelope: `{"error": {"code", "message"}}`

Update [http-api.md](http-api.md) and the contract tests together whenever the
live route set changes.
