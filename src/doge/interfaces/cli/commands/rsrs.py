"""CLI command: rsrs."""

import sys

import pandas as pd

from doge.application.composition import build_ranking_service
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
