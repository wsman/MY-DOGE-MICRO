"""Docs-consistency gate tests for ``docs/operations-runbook.md`` (WAVE2-DOC-RUNBOOK).

Three contracts, all pure file/static parsing (no network, no DB):

  1. **Shell-example validity** — every fenced-shell command block the runbook
     presents as runnable must (a) be syntactically valid under ``bash -n`` and
     (b) reference the env-var name (``DOGE_RETENTION_DAYS``) exactly as the
     settings layer reads it. Prevents an operator copy-pasting a broken or
     stale-env example.

  2. **Troubleshooting anchor validity** — the troubleshooting table's
     "expected cause -> fix" rows must cite their source anchors (file:line or
     CDD section). Each cited ``design/cdd/<x>.md`` / ``src/<...>.py`` /
     ``docs/architecture/adr-*.md`` path must resolve on disk, and the named
     CDD sections (e.g. ``market-data-storage.md`` §9.3 concurrency) must
     actually exist as headers in those files.

  3. **Retention section reality** — the retention-tuning section must document
     the SHIPPED ``DOGE_RETENTION_DAYS`` default of 730 (S002-007) and the
     destructive per-ticker prune, not a hypothetical/future state.

Determinism: pure filesystem + regex parsing, no external state.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = _REPO_ROOT / "docs" / "operations-runbook.md"
SETTINGS_PY = _REPO_ROOT / "src" / "doge" / "config" / "settings.py"

# bash may be available as `bash` (Git Bash / WSL) on this Windows host. The
# test skips the shell-syntax sub-contract if bash is absent rather than fail.
_HAS_BASH = None


def _bash_available() -> bool:
    global _HAS_BASH
    if _HAS_BASH is None:
        try:
            subprocess.run(
                ["bash", "--version"], capture_output=True, check=True, timeout=5
            )
            _HAS_BASH = True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            _HAS_BASH = False
    return _HAS_BASH


# ---------------------------------------------------------------------------
# Fixture: the runbook must exist and we read it once.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def runbook() -> str:
    assert DOC.is_file(), f"{DOC} must exist (WAVE2-DOC-RUNBOOK)"
    return DOC.read_text(encoding="utf-8")


def _fenced_shell_blocks(markdown: str) -> list[str]:
    """Return the contents of every ```bash fenced block in the markdown.

    Only ``bash``-fenced blocks are extracted — inline ``code`` is skipped
    (those are illustrative env-var names, not runnable commands). Blocks that
    contain a ``#``-only comment line with no command are still returned but
    contribute no executable statements; ``bash -n`` accepts them.
    """
    blocks: list[str] = []
    pattern = re.compile(r"```bash\n(.*?)```", re.DOTALL)
    for m in pattern.finditer(markdown):
        blocks.append(m.group(1))
    return blocks


# ---------------------------------------------------------------------------
# Contract 1: shell examples are syntactically valid + env-var names are real
# ---------------------------------------------------------------------------
class TestShellExamplesValid:
    def test_bash_blocks_parse_clean(self, runbook):
        """Every ```bash block must pass ``bash -n`` (syntax-only, no exec)."""
        if not _bash_available():
            pytest.skip("bash not available on this host — shell-syntax sub-contract skipped")

        blocks = _fenced_shell_blocks(runbook)
        assert blocks, "no ```bash blocks found — the regex is stale"

        failures: list[str] = []
        for idx, block in enumerate(blocks, start=1):
            # Strip pure-comment lines and blank lines so a block that is only
            # documentation comments still parses; bash -n tolerates them but
            # we want a clean signal for the operator-facing commands.
            proc = subprocess.run(
                ["bash", "-n"],
                input=block,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                failures.append(
                    f"bash block #{idx} failed bash -n:\n{block}\nstderr: {proc.stderr.strip()}"
                )
        assert not failures, (
            "docs/operations-runbook.md contains ```bash blocks that are not "
            "syntactically valid (operator copy-paste would fail): "
            + "\n---\n".join(failures)
        )

    def test_retention_env_var_name_matches_settings(self, runbook):
        """The runbook must use ``DOGE_RETENTION_DAYS`` — the exact name
        ``settings.py`` reads via ``_env_int("DOGE_RETENTION_DAYS", ...)``.

        A typo here (e.g. ``DOGE_RETENTION`` or ``RETENTION_DAYS``) would lead
        an operator to set an env var the code never reads.
        """
        # settings.py is the source of truth — extract the literal name.
        source = SETTINGS_PY.read_text(encoding="utf-8")
        m = re.search(r'_env_int\(\s*"([A-Z_][A-Z0-9_]+)"\s*,\s*730', source)
        assert m, "settings.py no longer reads the 730-default retention env var — test is stale"
        canonical_name = m.group(1)
        assert canonical_name == "DOGE_RETENTION_DAYS", (
            f"settings.py retention env var is {canonical_name!r}, expected DOGE_RETENTION_DAYS"
        )

        assert canonical_name in runbook, (
            f"runbook must reference the retention env var {canonical_name} by its "
            f"canonical name (a typo would silently no-op)."
        )


# ---------------------------------------------------------------------------
# Contract 2: troubleshooting anchors cite real sources
# ---------------------------------------------------------------------------
class TestTroubleshootingAnchorsResolve:
    def _referenced_source_paths(self, markdown: str) -> set[str]:
        """Pull repo-relative ``src/..``/``design/..``/``docs/..`` paths the
        runbook cites (file pointers, not runnable commands). Captures the
        kinds of anchors the troubleshooting table uses."""
        pattern = re.compile(
            r"(?:src/|design/|docs/|tests/)"
            r"[A-Za-z0-9_./\-]+\.(?:py|md|sql|yaml|json)"
        )
        return {m.group(0).replace("\\", "/") for m in pattern.finditer(markdown)}

    def test_cited_source_files_exist(self, runbook):
        referenced = self._referenced_source_paths(runbook)
        assert referenced, "no source paths were extracted — the regex is stale"

        missing = [p for p in sorted(referenced) if not (_REPO_ROOT / p).exists()]
        assert not missing, (
            "docs/operations-runbook.md cites source paths that do not resolve on "
            "disk (an operator following the citation would hit a missing file): "
            + ", ".join(missing)
        )

    def test_troubleshooting_cites_concurrency_section(self, runbook):
        """The 'database is locked' row must cite the concurrency model — the
        canonical home for the no-WAL/no-busy_timeout contract."""
        # The 'database is locked' symptom must appear, and it must cite
        # market-data-storage.md (the CDD whose §9.3 documents the lock).
        assert "database is locked" in runbook, (
            "troubleshooting table must include the 'database is locked' row"
        )
        assert "market-data-storage.md" in runbook, (
            "'database is locked' row must cite market-data-storage.md (§9.3 concurrency)"
        )
        # The cited CDD must actually contain the concurrency heading and the
        # WAL/busy_timeout text the runbook claims it does.
        cdd = (_REPO_ROOT / "design/cdd/market-data-storage.md").read_text(encoding="utf-8")
        assert "Concurrency model" in cdd, (
            "design/cdd/market-data-storage.md §9.3 'Concurrency model' heading is missing "
            "— the runbook citation target has drifted"
        )
        assert "busy_timeout" in cdd and "database is locked" in cdd, (
            "design/cdd/market-data-storage.md must still document the no-busy_timeout / "
            "'database is locked' behavior the runbook cites"
        )

    def test_retention_troubleshooting_cites_view_window(self, runbook):
        """The breadth-truncation row must cite both the 730-day view window
        and the retention-vs-window safety guard."""
        assert "vw_market_breadth_cn" in runbook, (
            "retention/breadth troubleshooting must name the 730-day view window"
        )
        assert "test_retention_view_window_safety" in runbook, (
            "retention troubleshooting must cite the retention-vs-window safety guard test"
        )
        guard = _REPO_ROOT / "tests/migration/test_retention_view_window_safety.py"
        assert guard.is_file(), (
            "the cited retention-view-window guard test must exist on disk"
        )


# ---------------------------------------------------------------------------
# Contract 3: retention section reflects shipped reality (S002-007)
# ---------------------------------------------------------------------------
class TestRetentionSectionReflectsShippedReality:
    def test_default_730_documented(self, runbook):
        """S002-007 shipped a 730-day default; the runbook must state 730 as
        the live default (not a future/hardcoded-180 state)."""
        assert "730" in runbook, "runbook must document the shipped 730-day default"

    def test_retention_is_env_configurable(self, runbook):
        """The retention section must document that retention is env-driven via
        ``DOGE_RETENTION_DAYS`` (S002-007 / ADR-0002), not hardcoded."""
        assert "`DOGE_RETENTION_DAYS`" in runbook, (
            "runbook must document DOGE_RETENTION_DAYS as the env-configurable knob"
        )

    def test_destructive_prune_documented(self, runbook):
        """Retention is DESTRUCTIVE (per-ticker DELETE) — the runbook must warn."""
        assert "DESTRUCTIVE" in runbook or "destructive" in runbook, (
            "runbook must flag retention_days as destructive (per-ticker DELETE, no undo)"
        )

    def test_warmup_caveat_documented(self, runbook):
        """The TDX MAX_DAYS=120 warm-up caveat (no instant backfill) must be
        documented so an operator does not expect 730 days immediately."""
        assert "MAX_DAYS" in runbook or "120" in runbook, (
            "runbook must document the TDX MAX_DAYS=120 ingest ceiling / no-backfill caveat"
        )

    def test_settings_default_matches_doc(self, runbook):
        """settings.py must still declare 730 as the default — otherwise the
        runbook's 'Default: 730' claim has drifted."""
        source = SETTINGS_PY.read_text(encoding="utf-8")
        # The _env_int default literal must be 730.
        m = re.search(r'_env_int\(\s*"DOGE_RETENTION_DAYS"\s*,\s*(\d+)\s*\)', source)
        assert m, "settings.py no longer declares DOGE_RETENTION_DAYS — test is stale"
        assert m.group(1) == "730", (
            f"settings.py DOGE_RETENTION_DAYS default is {m.group(1)}, but the runbook "
            f"documents 730 — the doc has drifted from the shipped default"
        )


# ---------------------------------------------------------------------------
# Contract 4: DeepSeek key environment-verification section reflects shipped reality (S002-013)
# ---------------------------------------------------------------------------
class TestDeepSeekKeySectionReflectsShippedReality:
    def test_env_primary_documented(self, runbook):
        assert "`DEEPSEEK_API_KEY`" in runbook
        assert "PRIMARY" in runbook, (
            "key-verification section must state DEEPSEEK_API_KEY is the PRIMARY source (S002-013)"
        )

    def test_placeholder_sentinel_documented(self, runbook):
        assert "REPLACE_WITH_DEEPSEEK_API_KEY" in runbook, (
            "key-verification section must document the shipped placeholder sentinel"
        )

    def test_verification_procedure_steps_present(self, runbook):
        """The verification procedure must cover set -> restart -> verify, and
        must NOT include a REVOKE step (no key rotation is required per the
        history note; the word REVOKE does not appear in the section)."""
        for step in ("SET", "RESTART", "VERIFY"):
            assert step in runbook, (
                f"key-verification procedure must include the {step} step"
            )
        assert "REVOKE" not in runbook, (
            "the word REVOKE must not appear in the runbook section — "
            "no key rotation or history rewrite is required per shipped reality"
        )

    def test_config_py_raises_on_missing(self):
        """config.py must still raise RuntimeError on a missing/placeholder
        key — otherwise the runbook's RuntimeError guidance is stale."""
        source = (_REPO_ROOT / "src/macro/config.py").read_text(encoding="utf-8")
        assert "REPLACE_WITH_DEEPSEEK_API_KEY" in source, (
            "src/macro/config.py must still reference the placeholder sentinel"
        )
        assert "raise RuntimeError" in source, (
            "src/macro/config.py must still raise RuntimeError on a missing key (S002-013)"
        )
