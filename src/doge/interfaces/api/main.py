"""
MY-DOGE-MICRO FastAPI Backend
Tauri sidecar - runs on localhost:8901
"""

from __future__ import annotations

import os

# S002-009 / TR-011: project root sourced from get_settings() (ADR-0001
# forbidden pattern ``_PROJECT_ROOT`` dirname-walk). The module-global name is
# KEPT so the contract test (tests/test_api_routers.py:153) can still
# monkeypatch it to a temp dir; only the *derivation* changed (settings vs
# os.path.dirname walk).

# OpenBLAS safety settings.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from doge.config import get_settings
from doge.interfaces.api.app_factory import create_app
from doge.interfaces.api.auth import (
    _build_api_auth_provider,
    _has_oidc_config,
    _validate_api_auth_startup,
)
from doge.interfaces.api.middleware import _LEGACY_API_SUNSET
from doge.interfaces.api.routes import (
    _register_legacy_api_routes,
    _register_v1_routes,
    _should_mount_legacy_api,
    health,
    stats,
)
from doge.interfaces.api.startup_gates import (
    _LOOPBACK_HOSTS,
    _configured_bind_host,
    _resolve_bind_host,
    _validate_api_remote_bind_startup,
)

# Module-global project root - derived from Settings, monkeypatchable in tests.
_PROJECT_ROOT = str(get_settings().project_root)

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=_resolve_bind_host(), port=8901)
