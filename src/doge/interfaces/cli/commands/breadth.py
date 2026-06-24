"""CLI command: breadth."""

import sys

import pandas as pd

from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA
from doge.interfaces.cli.formatters import fmt_breadth_table


def cmd_breadth(args) -> None:
    """Query market breadth (advancers/decliners) via BreadthService."""
    data = build_breadth_service().breadth(args.market, args.days)

    if not data:
        print("no data")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(fmt_breadth_table(df))


def _gateway_container():
    return build_gateway_container()


def build_breadth_service():
    return _gateway_container().build_breadth_service()
