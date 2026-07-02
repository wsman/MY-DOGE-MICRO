"""Docs-consistency gate: README quickstart references real on-disk entrypoints.

This is a BLOCKING migration test for story WAVE2-DOC-README. It prevents the
README's "快速开始" (quick-start) section from drifting away from real
entrypoints: every script path and python entrypoint named in the active
quick-entry surfaces (MCP / FastAPI+web) MUST resolve on disk.

What this test guards (the active quick-entry surfaces in README.md):

  Surface A — MCP server:
      scripts/mcp_stdio.bat        (Windows stdio)
      scripts/mcp_stdio.sh         (POSIX stdio)
      scripts/start_mcp_sse.bat    (Windows SSE)
      scripts/start_mcp_sse.sh     (POSIX SSE)
      doge_mcp.py                  (the entrypoint the scripts invoke)

  Surface B — FastAPI + Vue web console:
      src/doge/interfaces/api/main.py
                                  (FastAPI backend, binds 127.0.0.1:8901)
      web/package.json             (the npm project `cd web && npm run dev` runs)

  Plus the config-template reference:
      models_config.template.json  (ships the REPLACE_WITH_DEEPSEEK_API_KEY sentinel)

If any of these disappears or is renamed, this test fails and forces the README
to be updated in lockstep — a docs-consistency gate, not a runtime test. It
performs NO network access and does NOT execute the entrypoints.

Regression anchor for S002-008/S002-013 shipped behavior:
  - README must NOT instruct operators to write a real API key into
    models_config.json (the section must mention DEEPSEEK_API_KEY env).
"""
from pathlib import Path

import pytest

# Test shim: project root is two levels up from this test file
# (tests/migration/test_readme_quickstart_commands.py -> <root>).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Entry points the README quick-start names — every one must exist on disk ──
# (kept as a literal tuple so the test is self-documenting and easy to extend)
REQUIRED_QUICKSTART_PATHS = (
    # Surface A — MCP server
    "scripts/mcp_stdio.bat",
    "scripts/mcp_stdio.sh",
    "scripts/start_mcp_sse.bat",
    "scripts/start_mcp_sse.sh",
    "doge_mcp.py",
    # Surface B — FastAPI + web console
    "src/doge/interfaces/api/main.py",
    "web/package.json",
    # Config template referenced in the API-key setup step
    "models_config.template.json",
    # Centralized settings (single source of truth cited by the README)
    "src/doge/config/settings.py",
)


@pytest.mark.parametrize("rel_path", REQUIRED_QUICKSTART_PATHS)
def test_quickstart_referenced_path_exists_on_disk(rel_path: str) -> None:
    """Every script/entrypoint named in the README quick-start must exist.

    Args:
        rel_path: project-root-relative path the README names verbatim.

    Fails loud if a quick-start reference has drifted from the real tree —
    the README is the most-read doc and must never point at a missing file.
    """
    target = _PROJECT_ROOT / rel_path
    assert target.exists(), (
        f"README quick-start references '{rel_path}' but it does not exist "
        f"at {target}. Update README.md or restore the entrypoint."
    )


def test_readme_quickstart_section_names_active_surfaces() -> None:
    """The README quick-start must present the active runtime surfaces.

    Guards against an accidental revert to the old single-surface desktop
    instruction after the Sprint M PyQt removal.
    """
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    # Each surface's headline entrypoint must appear in the quick-start region.
    required_entrypoints = {
        "scripts/mcp_stdio.bat": "MCP stdio entrypoint",
        "src/doge/interfaces/api/main.py": "FastAPI backend entrypoint",
    }
    for entrypoint, label in required_entrypoints.items():
        assert entrypoint in readme, (
            f"README quick-start is missing the {label} ({entrypoint}); "
            f"the quick-entry must reference every active runtime surface."
        )


def test_readme_flags_deepseek_key_env_not_committed_key() -> None:
    """The README must steer operators to DEEPSEEK_API_KEY env (S002-013).

    The committed models_config.json / models_config.template.json ship only the
    REPLACE_WITH_DEEPSEEK_API_KEY sentinel; the README must NOT instruct
    operators to write a real key into models_config.json.
    """
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY" in readme, (
        "README must reference the DEEPSEEK_API_KEY env var (S002-013 makes env "
        "the single source of truth for the key)."
    )
    assert "REPLACE_WITH_DEEPSEEK_API_KEY" in readme, (
        "README should document that the shipped config carries the "
        "REPLACE_WITH_DEEPSEEK_API_KEY placeholder, not a real key."
    )


def test_readme_marks_pyqt_dashboard_as_removed() -> None:
    """The README must not advertise the retired PyQt dashboard as runnable."""
    readme = (_PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "PyQt desktop dashboard" in readme
    assert "removed" in readme
    assert "python src/interface/dashboard.py" not in readme
    assert 'pip install -e ".[gui]"' not in readme
