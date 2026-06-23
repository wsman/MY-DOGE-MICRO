from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_pre_commit_readiness import validate


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_pre_commit_readiness_fast_runs_required_validators():
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = validate(mode="fast", runner=runner)

    assert result["passed"] is True
    assert result["remote_ci_post_commit_required"] is True
    command_text = "\n".join(" ".join(call) for call in calls)
    assert "scripts/validate_alpha_pre_remote_ci_package.py" in command_text
    assert "scripts/validate_alpha_pending_payload.py" in command_text
    assert "scripts/validate_alpha_maturity_honesty.py" in command_text
    assert "scripts/validate_alpha_commit_scope.py" in command_text
    assert "scripts/validate_plan_closure_gate.py --allow-open" in command_text
    assert "scripts/validate_plan_closure_handoff.py" in command_text
    assert "git diff --check" in command_text


def test_alpha_pre_commit_readiness_full_adds_focused_tests():
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = validate(mode="full", runner=runner)

    assert result["passed"] is True
    command_text = "\n".join(" ".join(call) for call in calls)
    assert "tests/unit/qa/test_validate_alpha_pre_commit_readiness.py" in command_text
    assert "tests/unit/governance/test_s017_planning_docs.py" in command_text
    assert "tests/unit/governance/test_adr_lifecycle_status.py" in command_text


def test_alpha_pre_commit_readiness_skip_pending_scope_omits_status_dependent_checks():
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = validate(mode="fast", runner=runner, include_pending_scope=False)

    assert result["passed"] is True
    assert result["pending_scope_checked"] is False
    command_text = "\n".join(" ".join(call) for call in calls)
    assert "scripts/validate_alpha_pending_payload.py" not in command_text
    assert "scripts/validate_alpha_commit_scope.py" not in command_text
    assert "scripts/validate_alpha_pre_remote_ci_package.py" in command_text
    assert "scripts/validate_alpha_maturity_honesty.py" in command_text


def test_alpha_pre_commit_readiness_reports_failed_command():
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if any("validate_alpha_commit_scope.py" in part for part in command):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="bad scope")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = validate(mode="fast", runner=runner)

    assert result["passed"] is False
    assert "alpha_commit_scope failed with exit code 1" in result["errors"]


def test_alpha_pre_commit_readiness_reports_failed_git_diff_check():
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command == ["git", "diff", "--check"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="whitespace")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = validate(mode="fast", runner=runner)

    assert result["passed"] is False
    assert "git_diff_check failed with exit code 1" in result["errors"]


def test_alpha_pre_commit_readiness_rejects_unknown_mode():
    try:
        validate(mode="wide")
    except ValueError as exc:
        assert "unsupported mode" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_alpha_pre_commit_readiness_cli_fast():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_alpha_pre_commit_readiness.py"),
            "--mode",
            "fast",
            "--skip-pending-scope",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout
    assert '"pending_scope_checked": false' in result.stdout
