"""Infrastructure-owned helpers for the TDX data-source adapter."""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def find_working_server(servers: list[str], test_market: str, timeout: float = 5) -> tuple[Any | None, str | None]:
    """Probe configured TDX servers and return the first working client."""
    try:
        from opentdx.tdxClient import TdxClient  # type: ignore[import-not-found]
    except ImportError:
        logger.info("opentdx unavailable; cannot probe TDX servers")
        return None, None

    candidates = list(servers[:20])
    if not candidates:
        return None, None

    def _test(host: str) -> tuple[Any | None, str | None]:
        try:
            client = TdxClient()
            port = 7709 if test_market == "cn" else 7727
            client.quotation_client.connect(host, port=port, time_out=timeout)
            client.quotation_client.login()
            if test_market == "us":
                client.ex_quotation_client.connect(host, port=7727, time_out=timeout)
                client.ex_quotation_client.login()
            return client, host
        except Exception:
            return None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(candidates))) as pool:
        futures = {pool.submit(_test, host): host for host in candidates}
        try:
            for future in concurrent.futures.as_completed(futures, timeout=timeout + 2):
                client, host = future.result()
                if client is not None:
                    for pending in futures:
                        pending.cancel()
                    return client, host
        except concurrent.futures.TimeoutError:
            return None, None
    return None, None


def ticker_to_market_code(ticker: str) -> tuple[Any | None, str]:
    """Map a canonical CN ticker suffix to the corresponding TDX market enum."""
    try:
        from opentdx.const import MARKET  # type: ignore[import-not-found]
    except ImportError:
        return None, ticker.split(".")[0] if "." in ticker else ticker

    if "." not in ticker:
        return None, ticker
    code, suffix = ticker.split(".", maxsplit=1)
    suffix = suffix.upper()
    if suffix == "SH":
        return MARKET.SH, code
    if suffix == "SZ":
        return MARKET.SZ, code
    if suffix == "BJ":
        return MARKET.BJ, code
    return MARKET.SZ, code


def bars_to_df(bars: list[dict[str, Any]], ticker: str, max_rows: int = 120) -> pd.DataFrame | None:
    """Convert opentdx kline bars into the canonical OHLCV frame."""
    if not bars:
        return None
    frame = pd.DataFrame(bars)
    dt_col = "datetime" if "datetime" in frame.columns else "date_time"
    if dt_col not in frame.columns:
        return None
    frame["date"] = pd.to_datetime(frame[dt_col]).dt.strftime("%Y-%m-%d")
    frame = frame.rename(columns={"vol": "volume"})
    required = ["date", "open", "high", "low", "close", "volume", "amount"]
    if any(column not in frame.columns for column in required):
        return None
    frame = frame[required]
    frame["ticker"] = ticker
    frame = frame.sort_values("date")
    if len(frame) > max_rows:
        frame = frame.tail(max_rows).reset_index(drop=True)
    return frame


def get_latest_market_date(client: Any, market: str = "cn") -> str | None:
    """Read the latest observable market date from a connected TDX client."""
    try:
        from opentdx.const import EX_MARKET, MARKET, PERIOD  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        if market == "cn":
            bars = client.stock_kline(MARKET.SH, "000001", PERIOD.DAILY, start=0, count=5)
        else:
            bars = client.goods_kline(EX_MARKET.US_STOCK, "AAPL", PERIOD.DAILY, start=0, count=5)
        if not bars:
            return None
        dt_col = "datetime" if "datetime" in bars[0] else "date_time"
        return pd.to_datetime([bar[dt_col] for bar in bars]).max().strftime("%Y-%m-%d")
    except Exception:
        return None
