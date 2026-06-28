from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_maturity_honesty import REQUIRED_SNIPPETS, validate_texts


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_maturity_honesty_accepts_current_evidence_files():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_alpha_maturity_honesty.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout


def test_alpha_maturity_honesty_accepts_explicit_maturity_file_set():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_alpha_maturity_honesty.py"),
            "--file",
            "README.md",
            "--file",
            "docs/progress/runtime-maturity.yaml",
            "--file",
            "production/qa/evidence/architecture-remediation-acceptance-2026-06-28.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout


def test_alpha_maturity_honesty_rejects_direct_production_ready_claim():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] += "\nrelease_claim: production-ready\n"

    errors = validate_texts(files)

    assert any("possible unauthorized maturity promotion claim" in error for error in errors)


def test_alpha_maturity_honesty_allows_explicit_non_claim_context():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] += (
        "\nrelease_note: this is not production-ready and remains Alpha\n"
    )

    errors = validate_texts(files)

    assert errors == []


def test_alpha_maturity_honesty_rejects_missing_required_posture_snippet():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] = files[
        "docs/progress/runtime-maturity.yaml"
    ].replace("production_ready: false", "production_ready: true")

    errors = validate_texts(files)

    assert any(
        "docs/progress/runtime-maturity.yaml: missing required non-promotion snippet: production_ready: false"
        in error
        for error in errors
    )


def test_alpha_maturity_honesty_rejects_remains_approved_beta_claim():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] += (
        "\nrelease_note: enterprise beta remains approved for customers\n"
    )

    errors = validate_texts(files)

    assert any("possible unauthorized maturity promotion claim" in error for error in errors)


def test_alpha_maturity_honesty_rejects_non_forbidden_stable_declaration():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] += "\nstable_declaration: enabled\n"

    errors = validate_texts(files)

    assert any("stable_declaration must remain forbidden" in error for error in errors)


def test_alpha_maturity_honesty_rejects_non_experimental_level_3_label():
    files = _valid_files()
    files["docs/progress/runtime-maturity.yaml"] += "\nlevel_3_sdk_platform: stable\n"

    errors = validate_texts(files)

    assert any("level_3_sdk_platform must remain experimental" in error for error in errors)


def _valid_files() -> dict[str, str]:
    return {
        file_id: "\n".join(snippets)
        for file_id, snippets in REQUIRED_SNIPPETS.items()
    }
