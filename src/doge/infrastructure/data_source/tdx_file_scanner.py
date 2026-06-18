"""TDX local .day file scanner adapter.

Reads TDX binary daily files from a local vipdoc tree and produces canonical
OHLCV DataFrames. This is the canonical implementation of
:class:`~doge.core.ports.file_scanner.ITdxFileScanner`.

The parsing logic mirrors ``src.micro.tdx_loader.TDXReader`` but is
self-contained under ``doge.infrastructure`` so no ``src/doge`` module needs to
import ``micro.*``.
"""
from __future__ import annotations

import glob
import os
import re
import struct
from typing import Iterable, Optional

import pandas as pd

from doge.config import get_settings
from doge.core.ports.file_scanner import ITdxFileScanner, ProgressCallback


class TDXFileScanner(ITdxFileScanner):
    """Scan local TDX ``.day`` files into canonical OHLCV frames."""

    MAX_DAYS = 120
    CN_VALID_PREFIXES = ("00", "30", "60", "68")

    def __init__(self, max_days: int = MAX_DAYS):
        self._max_days = max_days

    def _autocorrect_path(self, tdx_path: str) -> str:
        """Resolve the vipdoc root directory.

        If ``tdx_path`` itself is named ``vipdoc`` it is used as-is; otherwise
        the ``vipdoc`` sub-directory is preferred when it exists.
        """
        if os.path.basename(tdx_path) == "vipdoc":
            return tdx_path
        candidate = os.path.join(tdx_path, "vipdoc")
        if os.path.exists(candidate):
            return candidate
        return tdx_path

    def list_tickers(self, market: str, tdx_path: str) -> list[str]:
        """Return tickers discoverable under ``tdx_path`` for ``market``."""
        root = self._autocorrect_path(tdx_path)
        if market == "cn":
            return self._list_cn_tickers(root)
        if market == "us":
            return self._list_us_tickers(root)
        raise ValueError(f"unknown market: {market!r}")

    def _list_cn_tickers(self, root: str) -> list[str]:
        tickers = []
        for market_dir in ("sh", "sz"):
            lday = os.path.join(root, market_dir, "lday")
            if not os.path.exists(lday):
                continue
            prefix = market_dir.lower()
            for path in glob.glob(os.path.join(lday, f"{prefix}*.day")):
                fname = os.path.basename(path)
                code = fname[2:-4]
                if code.startswith(self.CN_VALID_PREFIXES) and len(code) == 6:
                    tickers.append(f"{code}.{market_dir.upper()}")
        return sorted(set(tickers))

    def _list_us_tickers(self, root: str) -> list[str]:
        lday = os.path.join(root, "ds", "lday")
        if not os.path.exists(lday):
            return []
        tickers = []
        for path in glob.glob(os.path.join(lday, "*.day")):
            fname = os.path.basename(path)
            raw = fname.replace(".day", "")
            if "#" in raw:
                raw = raw.split("#")[-1]
            if re.match(r"^[A-Z]+$", raw) and "HK" not in raw:
                tickers.append(raw)
        return sorted(set(tickers))

    def scan_local(
        self,
        market: str,
        tdx_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Iterable[pd.DataFrame]:
        """Yield canonical OHLCV frames for every discoverable ticker."""
        root = self._autocorrect_path(tdx_path)
        tickers = self.list_tickers(market, root)
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            try:
                df = self._read_ticker(root, ticker, market)
            except Exception:
                # Per-ticker read failures are best-effort skipped, matching the
                # legacy ``market_scanner`` loop semantics.
                if progress_callback and (i % 50 == 0 or i == total - 1):
                    progress_callback(
                        int((i + 1) / total * 100), f"read failed: {ticker}"
                    )
                continue

            if df is not None and not df.empty:
                df["ticker"] = ticker
                yield df

            if progress_callback and (i % 50 == 0 or i == total - 1):
                progress_callback(
                    int((i + 1) / total * 100), f"scanning: {ticker}"
                )

        if progress_callback:
            progress_callback(100, "scan complete")

    def _read_ticker(self, root: str, ticker: str, market: str) -> Optional[pd.DataFrame]:
        """Parse the .day file for a single ticker."""
        if market == "cn":
            code, mkt = ticker.split(".")
            mkt_lower = mkt.lower()
            file_path = os.path.join(root, mkt_lower, "lday", f"{mkt_lower}{code}.day")
        else:
            pattern = os.path.join(root, "ds", "lday", f"*#{ticker}.day")
            files = glob.glob(pattern)
            if not files:
                return None
            file_path = files[0]

        if not os.path.exists(file_path):
            return None
        return self._parse_file(file_path, market)

    def _parse_file(self, file_path: str, market: str) -> pd.DataFrame:
        """Parse a single .day binary file."""
        records = []
        with open(file_path, "rb") as f:
            while True:
                data = f.read(32)
                if len(data) < 32:
                    break

                if market == "us":
                    unpacked = struct.unpack("<IfffffII", data)
                    date_int, open_f, high_f, low_f, close_f, amount_f, volume, _ = unpacked
                    date_str = self._format_date(date_int)
                    open_price = open_f
                    high_price = high_f
                    low_price = low_f
                    close_price = close_f
                else:
                    unpacked = struct.unpack("<IIIII fII", data)
                    date_int, open_i, high_i, low_i, close_i, amount_f, volume, _ = unpacked
                    date_str = self._format_date(date_int)
                    open_price = open_i / 100.0
                    high_price = high_i / 100.0
                    low_price = low_i / 100.0
                    close_price = close_i / 100.0

                records.append({
                    "date": date_str,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "amount": amount_f,
                })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = df.sort_values("date").reset_index(drop=True)
        if len(df) > self._max_days:
            df = df.tail(self._max_days).reset_index(drop=True)
        return df

    @staticmethod
    def _format_date(date_int: int) -> str:
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100
        return f"{year:04d}-{month:02d}-{day:02d}"
