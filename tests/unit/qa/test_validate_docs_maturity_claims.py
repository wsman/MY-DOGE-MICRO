from pathlib import Path
import subprocess
import sys

from scripts import validate_docs_maturity_claims as validator


ROOT = Path(__file__).resolve().parents[3]


def test_docs_maturity_claims_accepts_current_public_docs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_docs_maturity_claims.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout
    assert "doge.docs_maturity_claims.v1" in result.stdout


def test_docs_maturity_claims_rejects_direct_promotion_claim(tmp_path):
    doc = tmp_path / "claim.md"
    doc.write_text(
        "\n".join(
            [
                "# Claim",
                "production_ready: false",
                "stable_declaration: forbidden",
                "Level 3 | Experimental |",
                "release_note: production-ready for customers",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_docs_maturity_claims.py"),
            "--file",
            str(doc),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "possible unauthorized maturity promotion claim" in result.stdout


def test_docs_maturity_claims_scans_default_expected_files():
    payload = validator._read_files(validator.DEFAULT_DOC_FILES)

    assert "README.md" in payload
    assert "docs/progress/current-status.md" in payload
    assert "docs/progress/runtime-maturity.yaml" in payload
    assert "docs/product/runtime-levels.md" in payload
