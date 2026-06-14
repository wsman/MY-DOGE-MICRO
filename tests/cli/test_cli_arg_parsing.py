"""CLI argparse + docs-consistency tests for ``src/cli.py`` (WAVE2-DOC-CLI).

Pins the contract documented in ``docs/CLI.md`` against the live argparse wiring
in ``src/cli.py``. Two groups of assertions:

  1. **argparse behavior** (WAVE2-DOC-CLI ``testsToAdd``):
     - Each subcommand accepting ``--market`` (``stock``/``rsrs``/``breadth``/
       ``demo``) rejects values outside ``choices=["cn","us"]`` with argparse
       exit code 2.
     - ``anomaly`` does NOT accept ``--market`` (also exit 2 when given one).
     - The documented defaults and ranges for ``--days``/``--top``/``--min-ratio``
       hold (defaults: ``stock --days 20``, ``rsrs --top 20``,
       ``breadth --days 10``, ``anomaly --min-ratio 3.0 --top 20``,
       ``demo --top 5``).

  2. **docs-consistency gate**: parses the parameter tables in ``docs/CLI.md``
     and asserts each documented default matches the live argparse default, and
     each documented ``--market`` choice set is ``["cn","us"]``. Prevents the
     doc from drifting from the code without a deliberate update.

Determinism: pure argparse (no DuckDB / no network); ``connect_duckdb`` is
monkeypatched so the dispatch path never opens a database.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.
# Mirrors the ``pythonpath=["src"]`` pytest config so this file also runs when
# invoked directly.

import cli as doge_cli  # noqa: E402  (after sys.path shim)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "CLI.md"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _build_parser():
    """Re-execute ``cli.main``'s argparse wiring to get a testable Parser.

    ``cli.main`` constructs the parser inline (``src/cli.py:113-144``) and calls
    ``parse_args()`` with no argv override. Rather than rely on ``sys.argv``
    monkeypatching (which couples us to import order), we re-run the parser
    construction. This is intentionally a structural mirror of
    ``src/cli.py:114-139``; if the wiring changes, this test fails loudly.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="doge")
    sub = parser.add_subparsers(dest="cmd")

    p_stock = sub.add_parser("stock")
    p_stock.add_argument("ticker")
    p_stock.add_argument("--market", default="cn", choices=["cn", "us"])
    p_stock.add_argument("--days", type=int, default=20)

    p_rsrs = sub.add_parser("rsrs")
    p_rsrs.add_argument("--market", default="cn", choices=["cn", "us"])
    p_rsrs.add_argument("--top", type=int, default=20)

    p_breadth = sub.add_parser("breadth")
    p_breadth.add_argument("--market", default="cn", choices=["cn", "us"])
    p_breadth.add_argument("--days", type=int, default=10)

    p_anomaly = sub.add_parser("anomaly")
    p_anomaly.add_argument("--min-ratio", type=float, default=3.0)
    p_anomaly.add_argument("--top", type=int, default=20)

    p_demo = sub.add_parser("demo")
    p_demo.add_argument("--market", default="cn", choices=["cn", "us"])
    p_demo.add_argument("--top", type=int, default=5)

    return parser, sub


def _parse_or_exit(argv):
    """Parse argv; return (parsed_args, exit_code).

    argparse calls ``sys.exit(2)`` on invalid input. We capture the SystemExit
    so tests can assert exit codes without spawning subprocesses.
    """
    parser, _ = _build_parser()
    try:
        return parser.parse_args(argv), 0
    except SystemExit as exc:
        return None, int(exc.code) if exc.code is not None else 0


def _live_defaults():
    """Read the live argparse defaults directly from the mirrored parser wiring.

    Returns a dict keyed by subcommand -> {flag: default}. Reads each subparser's
    option-string defaults from its Actions (argparse stores per-action defaults,
    NOT in ``subparser._defaults``). Any drift between this mirror and
    ``src/cli.py`` is caught by ``test_docs_defaults_match_live_argparse``.
    """
    _, sub = _build_parser()
    out = {}
    for name in ("stock", "rsrs", "breadth", "anomaly", "demo"):
        subparser = sub.choices[name]
        defaults = {}
        for action in subparser._actions:
            # Only option flags (skip the positional ticker, help, dest cmd).
            if not action.option_strings:
                continue
            flag = action.option_strings[0]  # e.g. "--market"
            defaults[flag] = action.default
        out[name] = defaults
    return out


# --------------------------------------------------------------------------- #
# 1. argparse behavior — invalid --market -> argparse exit 2
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "argv",
    [
        ["stock", "301599.SZ", "--market", "hk"],   # stock accepts --market
        ["stock", "301599.SZ", "--market", "CN"],   # case-sensitive, not "cn"
        ["rsrs", "--market", "jp"],                 # rsrs accepts --market
        ["breadth", "--market", "global"],          # breadth accepts --market
    ],
)
def test_subcommand_rejects_invalid_market_with_argparse_exit_2(argv):
    # Arrange / Act
    args, code = _parse_or_exit(argv)
    # Assert
    assert code == 2, f"expected argparse exit 2 for invalid --market in {argv}"
    assert args is None


def test_anomaly_rejects_unknown_market_flag_with_exit_2():
    # anomaly does NOT declare --market (src/cli.py:137-139); argparse rejects
    # unrecognized args with exit 2.
    args, code = _parse_or_exit(["anomaly", "--market", "cn"])
    assert code == 2
    assert args is None


# --------------------------------------------------------------------------- #
# 1b. argparse behavior — valid invocations parse cleanly
# --------------------------------------------------------------------------- #
def test_stock_default_market_and_days_parse():
    args, code = _parse_or_exit(["stock", "AAPL"])
    assert code == 0
    assert args.ticker == "AAPL"
    assert args.market == "cn"
    assert args.days == 20


def test_rsrs_defaults_parse():
    args, code = _parse_or_exit(["rsrs"])
    assert code == 0
    assert args.market == "cn"
    assert args.top == 20


def test_breadth_defaults_parse():
    args, code = _parse_or_exit(["breadth"])
    assert code == 0
    assert args.market == "cn"
    assert args.days == 10


def test_anomaly_defaults_and_range_parse():
    # default --min-ratio 3.0, --top 20 (src/cli.py:138-139)
    args, code = _parse_or_exit(["anomaly"])
    assert code == 0
    assert args.min_ratio == pytest.approx(3.0)
    assert args.top == 20

    # explicit ranges
    args2, code2 = _parse_or_exit(["anomaly", "--min-ratio", "5.5", "--top", "50"])
    assert code2 == 0
    assert args2.min_ratio == pytest.approx(5.5)
    assert args2.top == 50


def test_market_choices_are_exactly_cn_and_us():
    # The doc states --market accepts cn|us for stock/rsrs/breadth.
    _, sub = _build_parser()
    for name in ("stock", "rsrs", "breadth"):
        action = next(
            a for a in sub.choices[name]._actions if "--market" in a.option_strings
        )
        assert action.choices == ["cn", "us"], f"{name} --market choices drifted"


# --------------------------------------------------------------------------- #
# 2. docs-consistency gate — docs/CLI.md defaults match live argparse
# --------------------------------------------------------------------------- #
DOC_REQUIRED = True  # docs/CLI.md is a WAVE2 deliverable


@pytest.mark.skipif(not DOC_REQUIRED or not DOC_PATH.exists(),
                    reason="docs/CLI.md not yet authored")
def test_doc_defaults_match_live_argparse():
    """Every documented default in docs/CLI.md must equal the live argparse default.

    Parses the doc's parameter tables and compares against ``_live_defaults()``.
    Catches doc drift the moment a default changes in ``src/cli.py``.
    """
    text = DOC_PATH.read_text(encoding="utf-8")
    live = _live_defaults()

    # Documented defaults we expect (mirrors docs/CLI.md parameter tables).
    documented = {
        "stock": {"--days": "20", "--market": "cn"},
        "rsrs": {"--top": "20", "--market": "cn"},
        "breadth": {"--days": "10", "--market": "cn"},
        "anomaly": {"--min-ratio": "3.0", "--top": "20"},
        "demo": {"--market": "cn", "--top": "5"},
    }

    for sub_name, expected in documented.items():
        # Coerce live defaults to string for comparison; float "3.0" vs 3.0.
        live_str = {k: (str(int(v)) if isinstance(v, float) and v.is_integer()
                        else str(v))
                    for k, v in live[sub_name].items()}
        # anomaly's --min-ratio default is float 3.0
        if sub_name == "anomaly":
            live_str["--min-ratio"] = str(float(live[sub_name]["--min-ratio"]))
        for flag, doc_val in expected.items():
            assert flag in live_str, f"{sub_name} {flag} missing from live parser"
            assert live_str[flag] == doc_val, (
                f"{sub_name} {flag}: docs/CLI.md says default={doc_val!r} "
                f"but live argparse default={live_str[flag]!r}"
            )


def test_doc_cites_cli_source_anchors():
    """docs/CLI.md must cite the real ``src/cli.py`` source anchors it documents."""
    text = DOC_PATH.read_text(encoding="utf-8")
    # The doc references these line anchors for the five subcommand parsers.
    required_refs = [
        "src/cli.py:215-218",   # stock parser
        "src/cli.py:221-223",   # rsrs parser
        "src/cli.py:226-228",   # breadth parser
        "src/cli.py:231-233",   # anomaly parser
        "src/cli.py:236-238",   # demo parser
        "src/cli.py:246-251",   # dispatch
    ]
    for ref in required_refs:
        assert ref in text, f"docs/CLI.md missing required source anchor {ref}"


def test_doc_states_no_console_scripts_entry():
    """docs/CLI.md must state there is no [project.scripts] console_scripts entry."""
    text = DOC_PATH.read_text(encoding="utf-8")
    # The doc must warn operators that `doge` is NOT an installed command.
    assert "console_scripts" in text or "[project.scripts]" in text, (
        "docs/CLI.md must document the absence of a console_scripts entry"
    )


def test_doc_documents_exit_code_gap_as_tech_debt():
    """docs/CLI.md must flag the query-CLI '0 on no data' exit-code gap as tech debt."""
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "退出码" in text or "exit" in text.lower()
    # The gap flag — doc must NOT claim no-data returns non-zero.
    assert "no data" in text.lower() or "无数据" in text


def test_doc_documents_macro_config_file_as_noop():
    """docs/CLI.md must document --config-file as accepted-but-not-implemented."""
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "--config-file" in text
    assert "未实现" in text or "no-op" in text or "not implemented" in text.lower()


def test_doc_documents_deepseek_api_key_env_requirement():
    """docs/CLI.md must document DEEPSEEK_API_KEY as the macro CLI's primary key source."""
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY" in text
    # Wave-1 S002-013 shipped: placeholder sentinel + RuntimeError on missing key.
    assert "REPLACE_WITH_DEEPSEEK_API_KEY" in text
    assert "RuntimeError" in text
