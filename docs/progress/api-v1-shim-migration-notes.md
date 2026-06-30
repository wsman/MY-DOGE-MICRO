# API v1 Shim Migration Notes

Canonical daemon gateway routers live under:

```text
doge.interfaces.gateway.routers
```

Compatibility import paths live under:

```text
doge.interfaces.api.routers.v1
```

Rules:

- New `/v1/*` behavior must be implemented in
  `doge.interfaces.gateway.routers`.
- `doge.interfaces.api.routers.v1` files must remain compatibility shims.
- Shim files may contain docstrings and re-export imports only. The documented
  `run_stream` compatibility export for `RunStreamHandler` is the current
  explicit exception.
- Removal is not before the existing compatibility deadline and requires import
  parity evidence plus client migration evidence.

Focused evidence:

```powershell
py -3 -m pytest tests\unit\architecture\test_gateway_router_shim_parity.py -q
py -3 -m pytest tests\unit\architecture -q
```
