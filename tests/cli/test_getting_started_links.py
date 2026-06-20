"""Docs-consistency gate tests for ``docs/GETTING_STARTED.md`` (WAVE2-DOC-GETTING_STARTED).

Two contracts, both pure file/static parsing (no network, no DB):

  1. **Path resolution** — every script path, doc link, and source file path
     the getting-started guide references as a runnable command or file
     pointer must actually resolve on disk. Prevents the guide from telling an
     operator to run a script that does not exist (or to read a doc that is
     not yet written).

  2. **Env-var superset** — the env-var table in the guide must be a superset
     of the configuration knobs declared in
     ``src/doge/config/settings.py`` ``DBConfig`` + ``MCPConfig`` + the
     ``MarketConfig.retention_days`` field. Prevents the doc from going stale
     when a new env-var-backed config field is added to settings.py.

Determinism: pure filesystem + regex parsing, no external state.
"""
import re
import sys
from pathlib import Path

import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable so
# we can import settings.py directly to read the live dataclass field names.
_REPO_ROOT = Path(__file__).resolve().parents[2]

DOC = _REPO_ROOT / "docs" / "GETTING_STARTED.md"
SETTINGS_PY = _REPO_ROOT / "src" / "doge" / "config" / "settings.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _referenced_relative_paths(markdown: str) -> set[str]:
    """Return repo-relative paths the guide points at.

    Captures, from inline backticks and fenced code blocks:
      - ``scripts/<name>.<bat|sh>``
      - ``docs/<name>.md``
      - ``src/<path>.py`` and bare ``<name>.py`` entrypoints
      - ``web/src/vendor/pretext/README.md`` and ``web/vite.config.ts``

    It deliberately skips:
      - absolute URLs (http://127.0.0.1:…)
      - environment-variable names (``DEEPSEEK_API_KEY`` etc. — no slash, no .py)
      - the machine-hardcoded ``E:\\LLMs\\...`` example (that is quoted inside
        a python fenced block and is illustrative of the bug, not a doc target)
    """
    text = markdown
    # Strip the illustrative Windows path so it is never mistaken for a doc
    # target. It is the literal bug example, not a file the doc points at.
    text = text.replace(r"E:\LLMs\miniconda3\Lib\site-packages\PyQt6\Qt6\bin", "")

    pattern = re.compile(
        r"(?:scripts/|scripts\\\\|docs/|src/|web/)"
        r"[A-Za-z0-9_./\\-]+\.(?:py|md|bat|sh|ts|json)"
    )
    found: set[str] = set()
    for match in pattern.finditer(text):
        # Normalise backslashes produced by Windows-style ``scripts\mcp_stdio.bat``
        candidate = match.group(0).replace("\\", "/")
        # Drop a trailing stray chars; the regex already bounds the extension.
        found.add(candidate)
    return found


# ---------------------------------------------------------------------------
# Contract 1: every referenced path resolves on disk
# ---------------------------------------------------------------------------
class TestGettingStartedPathsResolve:
    def test_document_exists(self):
        assert DOC.is_file(), f"{DOC} must exist (WAVE2-DOC-GETTING_STARTED)"

    def test_referenced_scripts_and_docs_resolve(self):
        # Arrange
        markdown = DOC.read_text(encoding="utf-8")
        referenced = _referenced_relative_paths(markdown)
        assert referenced, "no paths were extracted — the regex is stale"

        # Docs explicitly declared in the guide as "Wave 2; not yet written"
        # are referenced as plain-text next-steps targets (not markdown links)
        # and are authored by parallel agents. They are the ONLY allowed
        # not-yet-resolving references; every other path must resolve so the
        # guide never tells an operator to run a missing script or read a
        # missing file. When a Wave-2 doc ships, drop it from this allowlist.
        wave2_pending = {
            "docs/API.md",
            "docs/CLI.md",
            "docs/operations-runbook.md",
        }

        # Act / Assert — every referenced path resolves under the repo root,
        # unless it is an explicitly-pending Wave-2 doc.
        missing = []
        for rel in sorted(referenced):
            if rel in wave2_pending:
                continue
            if not (_REPO_ROOT / rel).exists():
                missing.append(rel)
        assert not missing, (
            "docs/GETTING_STARTED.md references paths that do not resolve on "
            "disk (operator would hit a missing-file error): "
            + ", ".join(missing)
        )

    def test_core_entrypoints_are_documented(self):
        """The guide must point at the three runtime entrypoints so an operator
        can actually find them — a guard against an accidental rewrite that
        drops a surface."""
        markdown = DOC.read_text(encoding="utf-8")
        required = {
            "src/doge/interfaces/api/main.py",
            "doge_mcp.py",
            "src/interface/dashboard.py",
            "scripts/mcp_stdio.bat",
            "scripts/start_mcp_sse.sh",
        }
        for path in required:
            assert path in markdown, (
                f"docs/GETTING_STARTED.md must reference {path} "
                f"(one of the three runtime surfaces)"
            )


# ---------------------------------------------------------------------------
# Contract 2: env-var table is a superset of settings.py config fields
# ---------------------------------------------------------------------------
class TestEnvVarTableSupersetOfSettings:
    """The doc's env-var table must not drift from settings.py.

    settings.py declares env-var-backed defaults inside the dataclasses via
    ``_env_path("NAME", …)`` / ``_env_int("NAME", …)`` calls. We extract every
    such NAME from settings.py and assert each appears as a row header in the
    doc's env-var tables. This is deliberately a *superset* check: the doc may
    document extra surface-level shell vars (e.g. ``MCP_HOST``/``MCP_PORT``
    honored by the start scripts) that are not dataclass fields.
    """

    def _settings_env_var_names(self) -> set[str]:
        """Pull every ``_env_path("X", …)`` / ``_env_int("X", …)`` literal name
        out of settings.py — these are the env vars settings.py actually reads."""
        source = SETTINGS_PY.read_text(encoding="utf-8")
        names: set[str] = set()
        for m in re.finditer(r'_env_(?:path|int)\(\s*"([A-Z_][A-Z0-9_]+)"', source):
            names.add(m.group(1))
        # MCPConfig dataclass-derived defaults surfaced through the start
        # scripts as MCP_HOST / MCP_PORT are documented separately and are not
        # _env_* calls — they are covered by the manual table, not asserted here.
        assert names, "no _env_* names parsed from settings.py — regex is stale"
        return names

    def test_doc_documents_every_settings_env_var(self):
        # Arrange — settings.py is the source of truth.
        settings_names = self._settings_env_var_names()
        markdown = DOC.read_text(encoding="utf-8")

        # Act — find each name as a markdown table row header (`` `NAME` ``).
        undocumented = [
            name for name in sorted(settings_names)
            if f"`{name}`" not in markdown
        ]

        # Assert — every settings-backed env var appears in the doc.
        assert not undocumented, (
            "docs/GETTING_STARTED.md env-var table is missing knobs that "
            "settings.py reads — the doc has drifted from the config source of "
            "truth (ADR-0002): " + ", ".join(undocumented)
        )

    def test_deepseek_and_retention_sections_present(self):
        """S002-013 (DEEPSEEK_API_KEY) and S002-007 (DOGE_RETENTION_DAYS)
        both shipped — the guide must document both as real (not placeholders)."""
        markdown = DOC.read_text(encoding="utf-8")
        # DEEPSEEK_API_KEY: documented and flagged as PRIMARY env source.
        assert "`DEEPSEEK_API_KEY`" in markdown
        assert "PRIMARY" in markdown, (
            "DEEPSEEK_API_KEY section must state it is the PRIMARY key source (S002-013)"
        )
        # DOGE_RETENTION_DAYS: documented with its destructive default.
        assert "`DOGE_RETENTION_DAYS`" in markdown
        assert "730" in markdown
        assert "DESTRUCTIVE" in markdown or "destructive" in markdown
