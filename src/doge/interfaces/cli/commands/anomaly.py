"""CLI command: anomaly."""

import sys

import pandas as pd

from doge.application.composition import build_anomaly_service
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
