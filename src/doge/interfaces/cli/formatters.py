"""Shared CLI table/markdown formatters."""

from typing import List

import pandas as pd
from tabulate import tabulate


def fmt_table(df: pd.DataFrame, columns: List[str], floatfmt=None) -> str:
    """Format a DataFrame subset with tabulate.

    Args:
        df: Input DataFrame.
        columns: Column subset to render.
        floatfmt: Optional tabulate ``floatfmt`` argument.
    """
    if df.empty:
        return ""
    return tabulate(
        df[columns],
        headers="keys",
        tablefmt="simple",
        showindex=False,
        floatfmt=floatfmt,
    )


def fmt_stock_table(data: List[dict]) -> str:
    """Format stock OHLCV query results."""
    df = pd.DataFrame(data)
    return tabulate(
        df,
        headers="keys",
        tablefmt="simple",
        showindex=False,
        floatfmt=(".0f", ".2f", ".2f", ".2f", ".2f", ".0f"),
    )


def fmt_rsrs_table(data: List[dict]) -> str:
    """Format RSRS ranking results."""
    df = pd.DataFrame(data)
    cols = ["rank", "ticker", "rsrs", "avg_vol_20d", "last_close"]
    if "pct_change_60d" in df.columns:
        cols.append("pct_change_60d")
    return tabulate(
        df[cols],
        headers="keys",
        tablefmt="simple",
        showindex=False,
        floatfmt=(".0f", ".6f", ".0f", ".2f", ".2f", ".2f"),
    )


def fmt_breadth_table(data: List[dict]) -> str:
    """Format market breadth results."""
    df = pd.DataFrame(data)
    return tabulate(
        df,
        headers="keys",
        tablefmt="simple",
        showindex=False,
        floatfmt=(".0f", ".0f", ".0f", ".2f", ".2f"),
    )


def fmt_anomaly_table(data: List[dict]) -> str:
    """Format volume anomaly results."""
    df = pd.DataFrame(data)
    return tabulate(
        df,
        headers="keys",
        tablefmt="simple",
        showindex=False,
        floatfmt=(".0f", ".2f", ".2f"),
    )
