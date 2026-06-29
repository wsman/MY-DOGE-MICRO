import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.build_enterprise_production_validation_evidence import build_evidence
from scripts.doged_live_idp_jwks_auth_smoke import _mask_operator_values, build_observations, redact_secrets
from scripts.validate_enterprise_production_validation_evidence import REQUIRED_CHECK_IDS, validate


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "doged_live_idp_jwks_auth_smoke.py"
LIVE_ENV_PREFIXES = ("DOGE_AUTH_OIDC_", "DOGE_LIVE_IDP_")


def test_doged_live_idp_jwks_auth_smoke_help_lists_runtime_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "--output-dir" in result.stdout
    assert "--timeout-seconds" in result.stdout
    assert "--port" in result.stdout
    assert "--date" in result.stdout
    assert "--sensitive" in result.stdout
    assert "--write-observations" in result.stdout
    assert "--token" not in result.stdout


def test_doged_live_idp_jwks_auth_smoke_missing_env_fails_without_traceback():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(LIVE_ENV_PREFIXES):
            env.pop(key)

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 2
    assert "missing required environment variables" in result.stderr
    assert "Traceback" not in result.stderr


def test_live_idp_redaction_masks_bearer_and_provider_key():
    payload = {
        "stdout_tail": "Authorization: Bearer abc.def.ghi",
        "stderr_tail": "provider key sk-testsecret",
    }

    redacted = redact_secrets(payload)

    assert redacted["stdout_tail"] == "Authorization: Bearer [REDACTED]"
    assert redacted["stderr_tail"] == "provider key sk-[REDACTED]"


def test_live_idp_sensitive_masking_hides_operator_urls_and_tenant():
    config = {
        "issuer": "https://idp.example.com/issuer",
        "audience": "doge-api",
        "jwks_url": "https://idp.example.com/.well-known/jwks.json",
        "expected_tenant_id": "tenant-live-smoke",
    }

    masked = _mask_operator_values(
        "issuer=https://idp.example.com/issuer jwks=https://idp.example.com/.well-known/jwks.json tenant-live-smoke",
        config,
        sensitive=True,
    )

    assert "https://idp.example.com" not in masked
    assert "tenant-live-smoke" not in masked
    assert "sha256:" in masked


def test_live_idp_observation_builder_includes_required_enterprise_checks(tmp_path):
    detailed = tmp_path / "live-idp-jwks-smoke-2026-06-29.json"
    detailed.write_text("{}", encoding="utf-8")

    observations = build_observations(
        detailed_smoke_path=detailed,
        live_passed=True,
        operator_evidence_ref="operator-secure-store://enterprise/live_idp_jwks/2026-06-29",
        executed_at="2026-06-29T00:00:00Z",
    )

    assert observations["result"] == "failed"
    assert set(observations["checks"]) == REQUIRED_CHECK_IDS
    assert observations["checks"]["live_idp_jwks"]["status"] == "passed"
    blocked = [key for key, value in observations["checks"].items() if value["status"] == "blocked"]
    assert set(blocked) == REQUIRED_CHECK_IDS - {"live_idp_jwks"}


def test_live_idp_success_observations_build_valid_enterprise_evidence(tmp_path):
    detailed = tmp_path / "live-idp-jwks-smoke-2026-06-29.json"
    detailed.write_text("{}", encoding="utf-8")
    observations_path = tmp_path / "enterprise-production-observations-2026-06-29.json"
    observations_path.write_text(
        json.dumps(
            build_observations(
                detailed_smoke_path=detailed,
                live_passed=True,
                operator_evidence_ref="operator-secure-store://enterprise/live_idp_jwks/2026-06-29",
                executed_at="2026-06-29T00:00:00Z",
            )
        ),
        encoding="utf-8",
    )

    payload = build_evidence(
        observations_path=observations_path,
        created_at="2026-06-29T00:00:00Z",
    )

    assert payload["result"] == "failed"
    assert validate(payload) == []
