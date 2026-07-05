"""Tests for the ``doge brief`` console market brief command."""

from __future__ import annotations

import pytest

from doge.application.contracts.response import MarketOverviewResponse
from doge.interfaces.cli.main import build_parser, main
from doge.interfaces.cli.commands import brief as brief_cmd


class _UseCase:
    def __init__(self):
        self.requests = []

    def brief(self, request):
        self.requests.append(request)
        return MarketOverviewResponse(
            market=request.market,
            markdown="\n".join(
                [
                    "# Market Brief",
                    "## 1. Market Regime",
                    "## 2. Breadth",
                    "## 3. Momentum Leaders",
                    "## 4. Volume Anomalies",
                    "## 5. Watchlist",
                    "## 6. Suggested Research Questions",
                ]
            ),
        )


def test_brief_parser_defaults_to_cn_and_top_20():
    parser = build_parser()

    args = parser.parse_args(["brief"])

    assert args.market == "cn"
    assert args.top == 20


def test_brief_prints_six_sections_for_cn(monkeypatch, capsys):
    use_case = _UseCase()
    monkeypatch.setattr(brief_cmd, "build_generate_market_overview_use_case", lambda: use_case)

    with pytest.raises(SystemExit) as exc:
        main(["brief", "--market", "cn", "--top", "6"])

    out = capsys.readouterr().out
    assert exc.value.code == 0
    assert use_case.requests[0].market == "cn"
    assert use_case.requests[0].top == 6
    for header in (
        "## 1. Market Regime",
        "## 2. Breadth",
        "## 3. Momentum Leaders",
        "## 4. Volume Anomalies",
        "## 5. Watchlist",
        "## 6. Suggested Research Questions",
    ):
        assert header in out


def test_brief_rejects_us_without_fabricating_data(monkeypatch, capsys):
    monkeypatch.setattr(
        brief_cmd,
        "build_generate_market_overview_use_case",
        lambda: pytest.fail("US brief should not build a market use case"),
    )

    with pytest.raises(SystemExit) as exc:
        main(["brief", "--market", "us"])

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "supports --market cn only" in captured.err
