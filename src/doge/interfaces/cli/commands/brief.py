"""CLI command: console market brief."""

from __future__ import annotations

import sys

from doge.application.contracts.request import GenerateMarketOverviewRequest
from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA


def cmd_brief(args) -> None:
    """Print a console-oriented market brief."""
    market = getattr(args, "market", "cn")
    if market != "cn":
        print("doge brief currently supports --market cn only; US local brief data is unavailable.", file=sys.stderr)
        sys.exit(EXIT_NO_DATA)
        return

    try:
        response = build_generate_market_overview_use_case().brief(
            GenerateMarketOverviewRequest(market=market, top=getattr(args, "top", 20))
        )
    except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
        print(f"brief failed: {exc}", file=sys.stderr)
        sys.exit(EXIT_NO_DATA)
        return

    print(response.markdown)
    sys.exit(0)


def build_generate_market_overview_use_case():
    return build_gateway_container().build_generate_market_overview_use_case()
