from dataclasses import dataclass

from doge.core.security import redact_secrets


@dataclass
class _Payload:
    api_key: str
    message: str
    nested: dict


def test_redact_secrets_recurses_through_dicts_lists_and_dataclasses():
    payload = _Payload(
        api_key="sk-secret-value",
        message=(
            "Authorization: Bearer bearer-secret "
            "MOONSHOT_API_KEY=moonshot-secret client_secret=client-secret sk-provider-secret"
        ),
        nested={
            "safe": ["ok", {"access_token": "access-secret"}],
            "note": "token=token-secret",
        },
    )

    redacted = redact_secrets(payload)
    rendered = str(redacted)

    assert redacted["api_key"] == "<redacted>"
    assert redacted["nested"]["safe"][1]["access_token"] == "<redacted>"
    assert "Bearer [REDACTED]" in rendered
    assert "MOONSHOT_API_KEY=<redacted>" in rendered
    assert "client_secret=<redacted>" in rendered
    assert "token=<redacted>" in rendered
    assert "sk-[REDACTED]" in rendered
    assert "moonshot-secret" not in rendered
    assert "client-secret" not in rendered
    assert "token-secret" not in rendered
