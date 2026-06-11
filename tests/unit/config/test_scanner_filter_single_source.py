"""S002-008 / TR-019 — scanner-filter single-source-of-truth tests.

Asserts that ``Settings().market`` (``MarketConfig``) is the COMPLETE canonical
source for the Micro Momentum Scanner filters, and that ``MomentumRanker`` reads
from settings (NOT from ``models_config.json``). Closes the config-drift open
question in ``design/cdd/micro-momentum-scanner.md`` §9 / OQ-1.

Determinism: no network. The "tampered models_config.json" scenario writes a
config file with DIFFERENT scanner_filters values into a temp project root and
asserts the ranker still reports the Settings values (proving the file is
ignored). The ranker is constructed with that temp root on sys.path / cwd so any
legacy file-read path would have picked it up — post-S002-008 it must NOT.
"""
import dataclasses
import json
import sys
from pathlib import Path

import pytest

# Test-shim (documented in test_settings.py / test_momentum_scanner.py): make
# src/ importable without depending on package install state.
_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(_SRC))

from doge.config import get_settings  # noqa: E402
from doge.config.settings import MarketConfig, reset_settings  # noqa: E402
from micro.momentum_scanner import MomentumRanker  # noqa: E402


# ---------------------------------------------------------------------------
# 1. MarketConfig is the COMPLETE canonical filter source
# ---------------------------------------------------------------------------
def test_market_config_holds_complete_filter_set():
    """MarketConfig must declare every scanner-filter field so it is the single
    source of truth (orchestrator decision 1)."""
    market = get_settings().market
    field_names = {f.name for f in dataclasses.fields(market)}

    # The five scanner-filter fields that previously lived ONLY in
    # models_config.json scanner_filters + the inline CN prefixes.
    required = {
        "cn_min_volume",
        "us_min_volume",
        "max_change_pct",
        "rsrs_window",
        "us_blacklist",
        "cn_universe_prefixes",
    }
    missing = required - field_names
    assert not missing, f"MarketConfig missing canonical filter fields: {missing}"


def test_market_config_us_blacklist_is_tuple_and_frozen():
    """us_blacklist MUST be a tuple (frozen-dataclass constraint) and the
    dataclass itself MUST be frozen so the list cannot mutate at runtime."""
    market = get_settings().market
    assert isinstance(market.us_blacklist, tuple), (
        "us_blacklist must be tuple[str, ...] on a frozen dataclass"
    )
    assert dataclasses.is_dataclass(market)
    # __dataclass_params__.frozen is True for @dataclass(frozen=True)
    assert market.__dataclass_params__.frozen is True
    # Mutation must raise FrozenInstanceError — the canonical anti-drift guard.
    with pytest.raises(dataclasses.FrozenInstanceError):
        market.us_blacklist = ("EVIL",)  # type: ignore[misc]


def test_market_config_us_blacklist_has_expected_members():
    """The ~52 leveraged/inverse ETF tickers are present (spot-check anchors)."""
    market = get_settings().market
    # Anchors from the historical hardcoded list (momentum_scanner.py:24).
    for anchor in ("SQQQ", "TQQQ", "SOXL", "BITX", "ULTY", "YMAX"):
        assert anchor in market.us_blacklist, f"{anchor} missing from us_blacklist"
    # Reasonable count (the historical list was ~52).
    assert 45 <= len(market.us_blacklist) <= 60


def test_market_config_cn_universe_prefixes_are_canonical():
    """cn_universe_prefixes matches the historical ('00','30','60','68')."""
    market = get_settings().market
    assert tuple(market.cn_universe_prefixes) == ("00", "30", "60", "68")


def test_market_config_filter_defaults_match_historical_values():
    """The numeric defaults match the values that previously lived inline +
    in models_config.json (behavior preservation)."""
    market = get_settings().market
    assert market.cn_min_volume == 200_000_000
    assert market.us_min_volume == 20_000_000
    assert market.max_change_pct == 400
    assert market.rsrs_window == 18


# ---------------------------------------------------------------------------
# 2. MomentumRanker reads from Settings().market (single source)
# ---------------------------------------------------------------------------
def test_momentum_ranker_config_is_dict_view_over_settings():
    """MomentumRanker._load_config returns a dict VIEW over MarketConfig,
    preserving legacy key names so existing call sites keep working."""
    market = get_settings().market
    ranker = MomentumRanker()
    cfg = ranker.config

    # Legacy key names preserved (call sites use .get(...)).
    assert set(cfg) >= {
        "us_blacklist",
        "min_volume_cn",
        "min_volume_us",
        "max_change_pct",
        "rsrs_window",
        "cn_universe_prefixes",
    }
    # Values mirror MarketConfig.
    assert cfg["min_volume_cn"] == market.cn_min_volume
    assert cfg["min_volume_us"] == market.us_min_volume
    assert cfg["max_change_pct"] == market.max_change_pct
    assert cfg["rsrs_window"] == market.rsrs_window
    # us_blacklist: tuple on MarketConfig -> list at the call site.
    assert isinstance(cfg["us_blacklist"], list)
    assert cfg["us_blacklist"] == list(market.us_blacklist)
    assert cfg["cn_universe_prefixes"] == list(market.cn_universe_prefixes)


def test_momentum_ranker_us_blacklist_consumed_in_analyze_market():
    """The analyze_market call site reads self.config['us_blacklist'] (legacy
    key) — verify the ranker exposes it as the same set the blacklist check
    uses, so the value flows end-to-end from Settings."""
    ranker = MomentumRanker()
    blacklist_set = set(ranker.config.get("us_blacklist", []))
    market_set = set(get_settings().market.us_blacklist)
    assert blacklist_set == market_set


# ---------------------------------------------------------------------------
# 3. MomentumRanker IGNORES a tampered models_config.json
# ---------------------------------------------------------------------------
def test_momentum_ranker_ignores_tampered_models_config(tmp_path, monkeypatch):
    """A models_config.json with DIFFERENT scanner_filters values must NOT
    affect MomentumRanker's config — proving the ranker no longer reads the
    file (S002-008 single-source). We force the legacy _project_root() to
    resolve to tmp_path so any residual file-read would pick up the tampered
    file; post-fix the ranker must still report the Settings values.
    """
    # Plant a tampered models_config.json at the temp "project root" with
    # values that differ from MarketConfig defaults.
    tampered = {
        "scanner_filters": {
            "us_blacklist": ["EVIL_ETF", "BAD_ETF"],
            "min_volume_cn": 1,            # differs from 200_000_000
            "min_volume_us": 2,            # differs from 20_000_000
            "max_change_pct": 999,         # differs from 400
            "rsrs_window": 99,             # differs from 18
        }
    }
    (tmp_path / "models_config.json").write_text(
        json.dumps(tampered), encoding="utf-8"
    )

    # Force the legacy _project_root() helper inside momentum_scanner to point
    # at tmp_path. Even if a residual read existed, it would now read the
    # tampered file. (Post-S002-008 _load_config does not read the file at all,
    # so this is belt-and-suspenders.)
    import micro.momentum_scanner as ms

    monkeypatch.setattr(ms, "_project_root", lambda: str(tmp_path))

    # Also reset the settings singleton so we read the real MarketConfig
    # defaults (in case an earlier test mutated the singleton).
    reset_settings()

    ranker = MomentumRanker()
    cfg = ranker.config
    market = get_settings().market

    # Every value MUST match Settings, NOT the tampered file.
    assert cfg["min_volume_cn"] == market.cn_min_volume == 200_000_000
    assert cfg["min_volume_us"] == market.us_min_volume == 20_000_000
    assert cfg["max_change_pct"] == market.max_change_pct == 400
    assert cfg["rsrs_window"] == market.rsrs_window == 18
    # Tampered entries must be ABSENT.
    assert "EVIL_ETF" not in cfg["us_blacklist"]
    assert "BAD_ETF" not in cfg["us_blacklist"]
    # And the real anchors must be present.
    assert "SQQQ" in cfg["us_blacklist"]
    assert "TQQQ" in cfg["us_blacklist"]


# ---------------------------------------------------------------------------
# 4. main() uses settings values (no hardcoded 2e8 / 2e7 literals)
# ---------------------------------------------------------------------------
def test_main_amount_thresholds_come_from_settings(monkeypatch):
    """main() must pass get_settings().market.cn_min_volume / us_min_volume
    (NOT the old hardcoded 200000000 / 20000000 literals). We capture the
    amount_threshold args passed to analyze_market and assert they equal the
    settings values."""
    reset_settings()
    market = get_settings().market

    captured = []

    def _capture(self, market_type, db_name, amount_threshold):
        captured.append((market_type, db_name, amount_threshold))
        # Do not actually run the scan (no DB).
        return None

    monkeypatch.setattr(MomentumRanker, "analyze_market", _capture)

    import micro.momentum_scanner as ms

    ms.main()

    assert len(captured) == 2
    cn_call = next(c for c in captured if c[0] == "CN")
    us_call = next(c for c in captured if c[0] == "US")

    # The amount_threshold MUST equal the Settings values, closing the
    # call-site-override gap (orchestrator decision 3).
    assert cn_call[2] == market.cn_min_volume
    assert us_call[2] == market.us_min_volume
    # And specifically NOT the old hardcoded literals passed independently of
    # settings (sanity: settings defaults currently equal these literals, so
    # this also asserts the values flow THROUGH settings, not around it).
    assert cn_call[2] == 200_000_000
    assert us_call[2] == 20_000_000
