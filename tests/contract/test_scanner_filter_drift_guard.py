"""S002-008 / TR-019 — BLOCKING drift guard for the scanner-filter single source.

Asserts that NO production ``.py`` module under ``src/micro``, ``src/macro``,
``src/api``, ``src/doge`` reads the ``scanner_filters`` key from
``models_config.json``. After S002-008 the ONLY source of scanner filters is
``Settings().market`` (``MarketConfig``); reintroducing a
``scanner_filters`` key-read would silently re-open the config-drift bug closed
by this story.

This is a grep-style contract test (per coding-standards.md: contract tests are
BLOCKING). It scans source text, so it catches both runtime key-reads AND
docstring-only mentions that pair the word with a bracket/dict-access — but it
is deliberately scoped to the **key-access literal** ``scanner_filters``
appearing inside a string-key context (``"scanner_filters"`` or
``'scanner_filters'``), which is the precise shape of a dict-key read. A bare
word mention in prose (e.g. ``# scanner_filters block``) is NOT flagged.
"""
import re
from pathlib import Path

import pytest

# Repository root: tests/contract/<this>.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Production source trees that must never reintroduce the scanner_filters
# key-read. The config router (src/doge/interfaces/api/routers/config.py) historically listed
# "scanner_filters" in a docstring as one of the preserved JSON fields; if it
# ever starts READING it as a key (post-removal the field is gone from the
# template), this guard fails.
_PROD_SOURCE_DIRS = [
    _REPO_ROOT / "src" / "micro",
    _REPO_ROOT / "src" / "macro",
    _REPO_ROOT / "src" / "api",
    _REPO_ROOT / "src" / "doge",
]

# Precise key-access literal: the token ``scanner_filters`` quoted as a string
# (double or single quotes). This matches dict-key reads like
# ``data["scanner_filters"]``, ``data.get("scanner_filters")``,
# ``'scanner_filters' in data``. It does NOT match prose mentions of the bare
# word, so legitimate docstrings that say "the scanner_filters section" without
# quoting it as a key are unaffected.
_KEY_ACCESS_RE = re.compile(r"""['"]scanner_filters['"]""")


def _iter_prod_py_files():
    """Yield every ``.py`` under the production source dirs."""
    for root in _PROD_SOURCE_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            yield path


def test_no_production_module_reads_scanner_filters_key():
    """BLOCKING: no production .py under src/{micro,macro,api,doge} may contain
    the ``scanner_filters`` key-access literal (quoted token)."""
    offenders = []
    for path in _iter_prod_py_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Some files in this brownfield repo are GBK; read with a tolerant
            # fallback so the guard never silently skips a file.
            text = path.read_text(encoding="utf-8", errors="replace")
        if _KEY_ACCESS_RE.search(text):
            offenders.append(path)

    if offenders:
        rel = "\n  ".join(str(p.relative_to(_REPO_ROOT)) for p in offenders)
        pytest.fail(
            "scanner_filters key-read reintroduced in production source "
            "(S002-008 closed this drift). Settings().market is the single "
            f"source of truth:\n  {rel}"
        )


def test_no_scanner_filters_section_in_tracked_template():
    """BLOCKING: the TRACKED models_config.template.json must NOT contain a
    ``scanner_filters`` section (the template is what commits; the live
    models_config.json is gitignored)."""
    template = _REPO_ROOT / "models_config.template.json"
    assert template.exists(), "models_config.template.json must exist"
    text = template.read_text(encoding="utf-8")
    # The bare key as a JSON member (with or without surrounding whitespace).
    assert not re.search(r'["\']?scanner_filters["\']?\s*:', text), (
        "models_config.template.json still has a scanner_filters section — "
        "scanner filters now live in Settings().market (S002-008)."
    )


def test_live_models_config_has_no_scanner_filters_section():
    """The live (gitignored) models_config.json should also have the section
    removed locally. This is NON-blocking if the file is absent (the template
    is the source of truth for new installs), but BLOCKING if the file exists
    and still carries scanner_filters (a local-only drift that would resurface
    if the file were ever committed)."""
    live = _REPO_ROOT / "models_config.json"
    if not live.exists():
        pytest.skip("models_config.json not present (template is the SoT)")
    text = live.read_text(encoding="utf-8")
    assert not re.search(r'["\']?scanner_filters["\']?\s*:', text), (
        "models_config.json still has a scanner_filters section — remove it "
        "(S002-008: filters live in Settings().market)."
    )
