"""Pure domain models — no external dependencies."""

from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import Optional


class MarketType(Enum):
    CN = auto()
    US = auto()


@dataclass(frozen=True)
class Ticker:
    """Normalized stock ticker."""
    code: str
    exchange: str  # "SH", "SZ", "BJ", or empty for US

    def __str__(self) -> str:
        if self.exchange:
            return f"{self.code}.{self.exchange}"
        return self.code


@dataclass(frozen=True)
class OHLCV:
    """Single day OHLCV record."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None


@dataclass(frozen=True)
class Stock:
    """Stock with metadata."""
    ticker: Ticker
    name_cn: Optional[str] = None
    name_en: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


@dataclass(frozen=True)
class RSRSRecord:
    """RSRS momentum ranking record."""
    ticker: Ticker
    rsrs: float
    rank: int
    last_close: float
    pct_change_60d: float
    avg_vol_20d: int


@dataclass(frozen=True)
class BreadthRecord:
    """Market breadth record."""
    date: date
    advancers: int
    decliners: int
    unchanged: int
    active: int
    avg_return_pct: float
    std_return_pct: float
    advance_ratio: Optional[float] = None


@dataclass(frozen=True)
class VolumeAnomaly:
    """Volume anomaly record."""
    ticker: Ticker
    date: date
    volume: int
    avg_vol_20d: float
    vol_ratio: float
    intraday_return: float
