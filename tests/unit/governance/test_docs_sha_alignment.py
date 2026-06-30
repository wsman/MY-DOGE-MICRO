from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LATEST_REMOTE_SHA = "6fd598ac223c390d81ea121d550d52afd3b47c87"
CURRENT_PUSHED_HEAD_SHA = "9f304a82ae603f0d15210d7cbfc4e502a61fea43"
SPRINT_B_COMMITTED_SHA = "fd1768fa690a9a0c3a8d7905a7b72f0af54f6b04"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_runtime_maturity_separates_latest_remote_sha_from_current_head() -> None:
    maturity = _read("docs/progress/runtime-maturity.yaml")

    assert "latest_remotely_verified_sha:" in maturity
    assert LATEST_REMOTE_SHA in maturity
    assert "latest remotely verified SHA 6fd598a passed" in maturity
    assert "current HEAD 6fd598a passed" not in maturity

    assert "current_pushed_head_local_evidence:" in maturity
    assert CURRENT_PUSHED_HEAD_SHA in maturity
    assert "remote_ci_result: failed" in maturity
    assert "remote_ci_run_id: 28423757545" in maturity
    assert "remote-ci-6fd598a.json" in maturity


def test_readme_does_not_claim_current_head_is_remotely_verified() -> None:
    readme = _read("README.md")

    assert f"The latest remotely verified SHA remains\n`{LATEST_REMOTE_SHA}`" in readme
    assert f"current pushed HEAD is\n`{CURRENT_PUSHED_HEAD_SHA}`" in readme
    assert "GitHub Actions run\n`28420166050`" in readme
    assert "run `28423757545` completed with result `failure`" in readme
    assert "remote-ci-6fd598a.json" in readme


def test_acceptance_report_targets_current_head_remote_ci_evidence() -> None:
    report = _read("production/qa/evidence/sprint-b-citation-evidence-acceptance-2026-06-28.md")

    assert f"Committed SHA: `{SPRINT_B_COMMITTED_SHA}`" in report
    assert "production/qa/evidence/ci/remote-ci-fd1768f.json" in report
    assert "GitHub Actions run `28326916286`" in report
    assert "Verdict: **GO**" in report
    assert "pending_exact_sha_evidence" not in report
    assert "03bfe4f6fd3256b3285d5538ecc68ace984a7815" not in report
    assert "78107e3e5b489a71f76337124309d8d290b26946" not in report


def test_ci_keeps_existing_docs_status_gates_without_duplicate_plan_step() -> None:
    workflow = _read(".github/workflows/ci.yml")

    for command in [
        "python scripts/validate_docs_links.py",
        "python scripts/validate_no_stale_counts.py",
        "python scripts/generate_docs_status.py --check",
    ]:
        assert workflow.count(command) == 1
