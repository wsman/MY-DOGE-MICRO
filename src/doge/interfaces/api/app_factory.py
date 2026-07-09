"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from doge.config import get_settings
from doge.interfaces.api.auth import _build_api_auth_provider, _validate_api_auth_startup
from doge.interfaces.api.errors import register_exception_handlers
from doge.interfaces.api.lifespan import lifespan
from doge.interfaces.api.middleware import register_middleware
from doge.interfaces.api.routes import register_routes


def create_app(settings=None) -> FastAPI:
    settings = settings or get_settings()
    auth_provider = _build_api_auth_provider(settings)
    _validate_api_auth_startup(settings, auth_provider)

    app = FastAPI(title="OpenDoge API", version="0.1.0", lifespan=lifespan)
    register_middleware(app, settings, auth_provider)
    register_exception_handlers(app)
    register_routes(app, settings)
    return app
