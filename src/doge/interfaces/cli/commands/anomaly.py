"""CLI command: anomaly."""

import sys

import pandas as pd

from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA
from doge.interfaces.cli.formatters import fmt_anomaly_table


def cmd_anomaly(args) -> None:
    """Query volume anomalies via AnomalyService."""
    data = build_anomaly_service().anomalies(args.min_ratio, args.top)

    if not data:
        print("no anomalies found")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(fmt_anomaly_table(df))


def _gateway_container():
    return build_gateway_container()


def build_anomaly_service():
    return _gateway_container().build_anomaly_service()
