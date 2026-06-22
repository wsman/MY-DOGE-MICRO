from scripts.evidence_redaction import secret_leak_errors


def test_secret_leak_errors_reject_credential_shapes_without_printing_values():
    payload = {
        "api_key": "sk-live-secret-value",
        "message": "Authorization: Bearer bearer-secret-value token=token-secret-value",
    }

    errors = secret_leak_errors(payload)

    assert any("unredacted sensitive field: $.api_key" in error for error in errors)
    assert any("provider-style API key" in error for error in errors)
    assert any("unredacted bearer credential" in error for error in errors)
    assert any("unredacted secret assignment" in error for error in errors)
    assert not any("secret-value" in error for error in errors)


def test_secret_leak_errors_accept_redacted_values_and_token_metadata():
    payload = {
        "api_key": "<redacted>",
        "note": "Bearer [REDACTED] token=<redacted> sk-[REDACTED]",
        "usage": {"total_tokens": 42, "cached_tokens": 4},
        "redaction_review": {"contains_secrets": False},
    }

    assert secret_leak_errors(payload) == []
