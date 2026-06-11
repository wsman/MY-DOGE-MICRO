"""Ticker name cache adapter — replaces global _ticker_names_cache dict.

Thread-safe, lazy-loaded, file-backed.
"""

import json
import os
import threading
from typing import Dict, Optional

from doge.config import get_settings
from doge.core.ports.cache import ITickerNameCache


class JSONTickerNameCache(ITickerNameCache):
    """Loads ticker names from local JSON, with in-memory LRU."""

    def __init__(self):
        self._settings = get_settings()
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict[str, str]] = {}  # market -> {ticker: name}

    def _path(self, market: str) -> str:
        return str(self._settings.data_dir / f"{market}_ticker_names.json")

    def _load_from_disk(self, market: str) -> Dict[str, str]:
        path = self._path(market)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def load(self, market: str) -> Dict[str, str]:
        with self._lock:
            if market not in self._cache:
                self._cache[market] = self._load_from_disk(market)
            return dict(self._cache[market])

    def get(self, ticker: str) -> Optional[str]:
        # Try CN first, then US
        for market in ("cn", "us"):
            names = self.load(market)
            if ticker in names:
                return names[ticker]
        return None

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
