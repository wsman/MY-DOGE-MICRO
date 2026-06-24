from fastapi import FastAPI
from fastapi.testclient import TestClient

from doge.config.settings import APIConfig, AuthConfig, Settings
from doge.interfaces.api import main as api_main


def _app(settings: Settings) -> FastAPI:
    app = FastAPI()
    api_main._register_legacy_api_routes(app, settings)
    api_main._register_v1_routes(app)
    return app


def test_enterprise_mode_does_not_mount_legacy_api_routes():
    settings = Settings(
        auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"),
        api=APIConfig(bind_host="127.0.0.1"),
    )
    client = TestClient(_app(settings))

    for path in (
        "/api/config",
        "/api/notes/recent",
        "/api/agent/runs/missing",
        "/api/documents",
        "/api/stats",
    ):
        assert client.get(path).status_code == 404

    assert client.get("/health").status_code == 200


def test_local_loopback_mode_keeps_legacy_api_routes():
    settings = Settings(
        auth=AuthConfig(mode="local_demo"),
        api=APIConfig(bind_host="127.0.0.1"),
    )
    client = TestClient(_app(settings))

    assert client.get("/api/config").status_code == 200
    assert client.get("/api/agent/runs/missing").status_code == 404
    assert any(route.path == "/api/stats" for route in client.app.routes)


def test_non_loopback_local_demo_does_not_mount_legacy_api_routes():
    settings = Settings(
        auth=AuthConfig(mode="local_demo"),
        api=APIConfig(bind_host="0.0.0.0"),
    )
    client = TestClient(_app(settings))

    assert client.get("/api/config").status_code == 404
    assert client.get("/api/notes/recent").status_code == 404
    assert client.get("/health").status_code == 200
