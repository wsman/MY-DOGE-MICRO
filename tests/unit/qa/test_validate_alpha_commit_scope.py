from pathlib import Path
import subprocess
import sys

import scripts.validate_alpha_commit_scope as commit_scope
from scripts.validate_alpha_commit_scope import analyze, analyze_material_scope
from scripts.validate_alpha_pending_payload import REQUIRED_PENDING_PATHS, REQUIRED_PENDING_PREFIXES


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_commit_scope_accepts_required_material_payload():
    status_lines = _required_status_lines()
    material_paths = _required_material_paths()

    result = analyze(status_lines, material_paths)

    assert result["passed"] is True
    assert result["errors"] == []
    assert result["unexpected_material_paths"] == []


def test_alpha_commit_scope_reports_status_only_unexpected_paths_without_failing():
    status_lines = _required_status_lines()
    status_lines.append(" M web/tsconfig.app.json")
    material_paths = _required_material_paths()

    result = analyze(status_lines, material_paths)

    assert result["passed"] is True
    assert result["non_material_unexpected_status_paths"] == ["web/tsconfig.app.json"]


def test_alpha_commit_scope_rejects_unexpected_material_path():
    status_lines = _required_status_lines()
    status_lines.append(" M src/unrelated.py")
    material_paths = _required_material_paths() | {"src/unrelated.py"}

    result = analyze(status_lines, material_paths)

    assert result["passed"] is False
    assert (
        "unexpected material paths in pending commit payload: src/unrelated.py"
        in result["errors"]
    )


def test_alpha_commit_scope_rejects_missing_required_path():
    status_lines = [
        f" M {path}"
        for path in REQUIRED_PENDING_PATHS
        if path != "scripts/verify_remote_ci_evidence.py"
    ]
    status_lines += [f" M {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    material_paths = {line[3:] for line in status_lines}

    result = analyze(status_lines, material_paths)

    assert result["passed"] is False
    assert (
        "required path missing from pending commit payload: scripts/verify_remote_ci_evidence.py"
        in result["errors"]
    )


def test_alpha_commit_scope_rejects_required_status_path_without_material_change():
    status_lines = _required_status_lines()
    material_paths = _required_material_paths() - {"scripts/verify_remote_ci_evidence.py"}

    result = analyze(status_lines, material_paths)

    assert result["passed"] is False
    assert result["missing_material_required_paths"] == ["scripts/verify_remote_ci_evidence.py"]
    assert (
        "required material path missing from pending commit payload: scripts/verify_remote_ci_evidence.py"
        in result["errors"]
    )


def test_alpha_material_scope_rejects_unexpected_commit_path():
    material_paths = _required_material_paths() | {"src/unrelated.py"}

    result = analyze_material_scope(material_paths)

    assert result["passed"] is False
    assert (
        "unexpected material paths in pending commit payload: src/unrelated.py"
        in result["errors"]
    )


def test_alpha_material_scope_rejects_missing_required_commit_path():
    material_paths = _required_material_paths() - {"scripts/verify_remote_ci_evidence.py"}

    result = analyze_material_scope(material_paths)

    assert result["passed"] is False
    assert result["missing_material_required_paths"] == ["scripts/verify_remote_ci_evidence.py"]


def test_alpha_commit_scope_cli_status_and_material_files(tmp_path):
    status_file = tmp_path / "status.txt"
    material_file = tmp_path / "material.txt"
    status_lines = [f"?? {path}" for path in REQUIRED_PENDING_PATHS]
    status_lines += [f"?? {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    material_paths = [path for path in REQUIRED_PENDING_PATHS]
    material_paths += [f"{prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    status_file.write_text("\n".join(status_lines), encoding="utf-8")
    material_file.write_text("\n".join(material_paths), encoding="utf-8")
    script = ROOT / "scripts" / "validate_alpha_commit_scope.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--status-file",
            str(status_file),
            "--material-paths-file",
            str(material_file),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout


def test_git_material_paths_include_staged_changes(monkeypatch):
    def fake_run(command, **kwargs):
        if command == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(command, 0, stdout="unstaged.py\n", stderr="")
        if command == ["git", "diff", "--cached", "--name-only"]:
            return subprocess.CompletedProcess(command, 0, stdout="staged.py\n", stderr="")
        if command == ["git", "ls-files", "--others", "--exclude-standard"]:
            return subprocess.CompletedProcess(command, 0, stdout="untracked.py\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(commit_scope.subprocess, "run", fake_run)

    assert commit_scope._git_material_paths() == {
        "staged.py",
        "unstaged.py",
        "untracked.py",
    }


def test_git_commit_material_paths_reads_diff_tree(monkeypatch):
    def fake_run(command, **kwargs):
        assert command == [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "abc123",
        ]
        return subprocess.CompletedProcess(command, 0, stdout="a.py\nb/c.py\n", stderr="")

    monkeypatch.setattr(commit_scope.subprocess, "run", fake_run)

    assert commit_scope.git_commit_material_paths("abc123") == {"a.py", "b/c.py"}


def test_git_commit_range_material_paths_reads_two_dot_diff(monkeypatch):
    def fake_run(command, **kwargs):
        assert command == [
            "git",
            "diff",
            "--name-only",
            "base123..head456",
        ]
        return subprocess.CompletedProcess(command, 0, stdout="a.py\nb/c.py\n", stderr="")

    monkeypatch.setattr(commit_scope.subprocess, "run", fake_run)

    assert commit_scope.git_commit_range_material_paths("base123", "head456") == {
        "a.py",
        "b/c.py",
    }


def _required_status_lines() -> list[str]:
    lines = [f" M {path}" for path in REQUIRED_PENDING_PATHS]
    lines += [f" M {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    return lines


def _required_material_paths() -> set[str]:
    paths = set(REQUIRED_PENDING_PATHS)
    paths.update(f"{prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES)
    return paths
