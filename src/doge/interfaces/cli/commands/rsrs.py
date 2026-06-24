"""CLI command: rsrs."""

import sys

import pandas as pd

from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA
from doge.interfaces.cli.formatters import fmt_rsrs_table


def cmd_rsrs(args) -> None:
    """Query the RSRS momentum ranking via RankingService."""
    data = build_ranking_service().rsrs(args.market, args.top)

    if not data:
        print("no data")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(fmt_rsrs_table(df))


def _gateway_container():
    return build_gateway_container()


def build_ranking_service():
    return _gateway_container().build_ranking_service()
