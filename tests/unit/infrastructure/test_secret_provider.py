import json
import sys

from doge.application import composition
from doge.config import reset_settings
from doge.infrastructure.secrets import EnvSecretProvider, ProcessSecretProvider


def test_env_secret_provider_resolves_canonical_secret_names(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot-secret")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret")
    provider = EnvSecretProvider()

    assert provider.get_secret("kimi.api_key") == "moonshot-secret"
    assert provider.get_secret("deepseek.api_key") == "deepseek-secret"


def test_env_secret_provider_treats_empty_values_as_missing(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "")
    provider = EnvSecretProvider()

    assert provider.get_secret("kimi.api_key") is None
    assert provider.get_secret("UNKNOWN_SECRET_NAME") is None


def test_process_secret_provider_appends_secret_name():
    provider = ProcessSecretProvider(
        command=(
            sys.executable,
            "-c",
            "import sys; print('secret-for-' + sys.argv[1])",
        ),
    )

    assert provider.get_secret("kimi.api_key") == "secret-for-kimi.api_key"


def test_process_secret_provider_uses_placeholder_and_allowlist():
    provider = ProcessSecretProvider(
        command=(
            sys.executable,
            "-c",
            "import sys; print('secret-for-' + sys.argv[1])",
            "{name}",
        ),
        allowed_names=frozenset({"kimi.api_key"}),
    )

    assert provider.get_secret("kimi.api_key") == "secret-for-kimi.api_key"
    assert provider.get_secret("deepseek.api_key") is None


def test_process_secret_provider_rejects_unsafe_secret_names():
    provider = ProcessSecretProvider(
        command=(
            sys.executable,
            "-c",
            "print('should-not-run')",
        ),
    )

    assert provider.get_secret("../bad") is None


def test_composition_selects_process_secret_provider(monkeypatch):
    command = [
        sys.executable,
        "-c",
        "import sys; print('configured-' + sys.argv[1])",
        "{name}",
    ]
    monkeypatch.setenv("DOGE_SECRET_PROVIDER", "process")
    monkeypatch.setenv("DOGE_SECRET_PROCESS_COMMAND_JSON", json.dumps(command))
    reset_settings()

    try:
        provider = composition.build_secret_provider()
        assert provider.get_secret("kimi.api_key") == "configured-kimi.api_key"
        assert provider.get_secret("not.allowed") is None
    finally:
        reset_settings()
