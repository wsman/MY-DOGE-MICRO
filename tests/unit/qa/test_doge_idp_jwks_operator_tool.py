import json
import os
from pathlib import Path
import subprocess
import sys

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from scripts import doge_idp_jwks_operator_tool as tool
from scripts.evidence_redaction import secret_leak_errors


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "doge_idp_jwks_operator_tool.py"
LIVE_ENV_PREFIXES = ("DOGE_AUTH_OIDC_", "DOGE_LIVE_IDP_")


def test_operator_tool_help_omits_raw_token_and_client_secret_flags():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )

    assert "jwks-inspect" in result.stdout
    assert "env-template" in result.stdout
    assert "make-invalid-signature" in result.stdout
    assert "run-smoke" in result.stdout
    assert "build-evidence" in result.stdout
    assert "--token" not in result.stdout
    assert "--client-secret" not in result.stdout


def test_jwks_inspect_writes_fingerprint_only_evidence(tmp_path, monkeypatch, capsys):
    output = tmp_path / "jwks-inspection.json"
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "live-key-1",
                "alg": "RS256",
                "use": "sig",
                "n": "modulus-public-value",
                "e": "AQAB",
            }
        ]
    }
    monkeypatch.setattr(tool, "_fetch_jwks", lambda _url, _timeout: jwks)

    result = tool.main(
        [
            "jwks-inspect",
            "--issuer",
            "https://idp.example.test/issuer",
            "--audience",
            "doge-api",
            "--jwks-url",
            "https://idp.example.test/.well-known/jwks.json",
            "--output",
            str(output),
            "--created-at",
            "2026-06-29T00:00:00Z",
            "--sensitive",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["result"] == "passed"
    assert payload["key_count"] == 1
    assert payload["keys"][0]["fingerprint"].startswith("sha256:")
    assert payload["keys"][0]["kid_fingerprint"].startswith("sha256:")
    rendered = json.dumps(payload, sort_keys=True)
    assert "modulus-public-value" not in rendered
    assert "live-key-1" not in rendered
    assert "https://idp.example.test" not in rendered
    assert secret_leak_errors(payload) == []
    assert "modulus-public-value" not in captured.out


def test_jwks_inspect_fails_closed_for_empty_jwks(monkeypatch, capsys):
    monkeypatch.setattr(tool, "_fetch_jwks", lambda _url, _timeout: {"keys": []})

    result = tool.main(
        [
            "jwks-inspect",
            "--issuer",
            "https://idp.example.test/issuer",
            "--audience",
            "doge-api",
            "--jwks-url",
            "https://idp.example.test/.well-known/jwks.json",
        ]
    )
    captured = capsys.readouterr()

    assert result == 1
    assert "JWKS contains no keys" in captured.out
    assert "Traceback" not in captured.err


def test_env_template_renders_paths_without_token_values(capsys):
    result = tool.main(
        [
            "env-template",
            "--issuer",
            "https://idp.example.test/issuer",
            "--audience",
            "doge-api",
            "--jwks-url",
            "https://idp.example.test/.well-known/jwks.json",
            "--valid-token-file",
            "C:\\secure\\doge\\valid.jwt",
            "--wrong-audience-token-file",
            "C:\\secure\\doge\\wrong-audience.jwt",
            "--expected-tenant-id",
            "tenant-live",
            "--operator-evidence-ref",
            "operator-secure-store://enterprise/live_idp_jwks/2026-06-29",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "$env:DOGE_LIVE_IDP_VALID_TOKEN_FILE" in captured.out
    assert "C:\\secure\\doge\\valid.jwt" in captured.out
    assert "Bearer " not in captured.out
    assert "client_secret" not in captured.out.lower()


def test_make_invalid_signature_writes_token_without_private_key(tmp_path, capsys):
    source_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    source_token = jwt.encode(
        {
            "iss": "https://idp.example.test/issuer",
            "aud": "doge-api",
            "sub": "operator@example.test",
            "tenant_id": "tenant-live",
        },
        source_private_key,
        algorithm="RS256",
        headers={"kid": "live-key-1"},
    )
    source = tmp_path / "valid.jwt"
    output = tmp_path / "invalid.jwt"
    source.write_text(source_token, encoding="utf-8")

    result = tool.main(["make-invalid-signature", "--like-token-file", str(source), "--output", str(output)])
    captured = capsys.readouterr()

    assert result == 0
    generated = output.read_text(encoding="utf-8").strip()
    assert generated
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(generated, source_private_key.public_key(), algorithms=["RS256"], audience="doge-api")
    assert "PRIVATE KEY" not in output.read_text(encoding="utf-8")
    assert source_token not in captured.out
    assert generated not in captured.out
    assert "output_token_fingerprint" in captured.out


def test_run_smoke_missing_env_fails_without_traceback(monkeypatch, capsys):
    for key in list(os.environ):
        if key.startswith(LIVE_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)

    result = tool.main(["run-smoke", "--date", "2026-06-29"])
    captured = capsys.readouterr()

    assert result == 2
    assert "missing required environment variables" in captured.err
    assert "Traceback" not in captured.err


def test_run_smoke_delegates_to_existing_runner(monkeypatch, capsys):
    commands: list[list[str]] = []

    def fake_load_config(_env):
        return {"ok": True}

    def fake_run(command, **kwargs):
        commands.append(command)
        assert kwargs["cwd"] == tool.ROOT
        assert kwargs["capture_output"] is True
        return subprocess.CompletedProcess(command, 0, stdout='{"result":"passed"}\n', stderr="")

    monkeypatch.setattr(tool.live_smoke, "load_config", fake_load_config)
    monkeypatch.setattr(tool.subprocess, "run", fake_run)

    result = tool.main(["run-smoke", "--date", "2026-06-29", "--port", "0"])
    captured = capsys.readouterr()

    assert result == 0
    command = commands[0]
    assert str(tool.ROOT / "scripts" / "doged_live_idp_jwks_auth_smoke.py") in command
    assert "--sensitive" in command
    assert "--write-observations" in command
    assert "--date" in command
    assert '{"result":"passed"}' in captured.out


def test_build_evidence_delegates_and_propagates_validator_failure(monkeypatch, capsys):
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            command,
            1,
            stdout='{"passed_validation": false, "errors": ["failed evidence requires issue_refs"]}\n',
            stderr="",
        )

    monkeypatch.setattr(tool.subprocess, "run", fake_run)

    result = tool.main(
        [
            "build-evidence",
            "--observations",
            "production/qa/evidence/enterprise/enterprise-production-observations-2026-06-29.json",
            "--output",
            "production/qa/evidence/enterprise/enterprise-production-validation-2026-06-29.json",
        ]
    )
    captured = capsys.readouterr()

    assert result == 1
    assert "build_enterprise_production_validation_evidence.py" in commands[0][1]
    assert "failed evidence requires issue_refs" in captured.out
