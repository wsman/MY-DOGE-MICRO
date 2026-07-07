"""Market data-source selection for slot-contributed sources."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Iterable

from doge.platform.slots import (
    DataSourceContribution,
    SlotConfigurationError,
    SlotContext,
)


@dataclass(frozen=True)
class _DataSourceEntry:
    source_id: str
    source: object
    markets: tuple[str, ...]


class DataSourceRegistry:
    """Market-aware proxy over slot-contributed data source instances."""

    def __init__(
        self,
        data_sources: Iterable[DataSourceContribution],
        context: SlotContext,
        *,
        preferred_source_id: str | None = None,
    ) -> None:
        entries: list[_DataSourceEntry] = []
        seen: set[str] = set()
        for contribution in data_sources:
            if contribution.source_id in seen:
                raise SlotConfigurationError(
                    f"duplicate data source contribution: {contribution.source_id}"
                )
            seen.add(contribution.source_id)
            source = contribution.factory(context)
            if source is None:
                raise SlotConfigurationError(
                    f"data source {contribution.source_id} returned no source"
                )
            entries.append(
                _DataSourceEntry(
                    source_id=contribution.source_id,
                    source=source,
                    markets=_normalize_markets(contribution.markets),
                )
            )
        if not entries:
            raise ValueError("DataSourceRegistry requires at least one source")
        if preferred_source_id is not None and preferred_source_id not in {
            entry.source_id for entry in entries
        }:
            raise SlotConfigurationError(
                f"unknown preferred data source: {preferred_source_id}"
            )
        self._entries = tuple(entries)
        self._preferred_source_id = preferred_source_id
        self._active_source_id: str | None = None
        self._active_market: str | None = None

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(entry.source_id for entry in self._entries)

    def source_for(self, market: str, source_id: str | None = None) -> object:
        resolved_market = _normalize_market(market)
        preferred = source_id or self._preferred_source_id
        candidates = [
            entry
            for entry in self._entries
            if _supports_market(entry.markets, resolved_market)
        ]
        if preferred is not None:
            candidates = [entry for entry in candidates if entry.source_id == preferred]
        if not candidates:
            suffix = f" with source {preferred}" if preferred else ""
            raise SlotConfigurationError(
                f"no data source supports market: {resolved_market or '<none>'}{suffix}"
            )
        return candidates[0].source

    def connect(self, market: str = "cn") -> None:
        source = self.source_for(market)
        _connect_source(source, market)
        self._active_source_id = _source_id_for(self._entries, source)
        self._active_market = _normalize_market(market)

    def disconnect(self) -> None:
        for entry in self._entries:
            disconnect = getattr(entry.source, "disconnect", None)
            if disconnect is not None:
                disconnect()
        self._active_source_id = None
        self._active_market = None

    def is_connected(self) -> bool:
        if self._active_source_id is None:
            return False
        source = self.source_for_active()
        is_connected = getattr(source, "is_connected", None)
        return bool(is_connected()) if is_connected is not None else False

    def download_kline(
        self,
        ticker: str,
        market: str,
        start: int = 0,
        count: int = 800,
    ):
        source = self.source_for(market)
        self._ensure_connected_for(source, market)
        return source.download_kline(ticker, market, start=start, count=count)

    def get_latest_market_date(self, market: str):
        source = self.source_for(market)
        return source.get_latest_market_date(market)

    def source_for_active(self) -> object:
        if self._active_source_id is None:
            raise SlotConfigurationError("no active data source")
        for entry in self._entries:
            if entry.source_id == self._active_source_id:
                return entry.source
        raise SlotConfigurationError(f"active data source missing: {self._active_source_id}")

    def _ensure_connected_for(self, source: object, market: str) -> None:
        source_id = _source_id_for(self._entries, source)
        connected = False
        is_connected = getattr(source, "is_connected", None)
        if is_connected is not None:
            connected = bool(is_connected())
        if (
            self._active_source_id != source_id
            or self._active_market != _normalize_market(market)
            or not connected
        ):
            _connect_source(source, market)
            self._active_source_id = source_id
            self._active_market = _normalize_market(market)


def _normalize_markets(markets: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(_normalize_market(market) for market in markets if market.strip())
    if not normalized:
        raise SlotConfigurationError("data source must declare markets")
    return normalized


def _normalize_market(market: str) -> str:
    return (market or "").strip().lower()


def _supports_market(markets: tuple[str, ...], market: str) -> bool:
    return "*" in markets or market in markets


def _connect_source(source: object, market: str) -> None:
    connect = getattr(source, "connect", None)
    if connect is None:
        raise SlotConfigurationError("data source does not expose connect()")
    mode = _market_argument_mode(connect)
    if mode == "positional":
        connect(market)
    elif mode == "keyword":
        connect(market=market)
    else:
        connect()


def _market_argument_mode(connect: object) -> str:
    try:
        parameters = signature(connect).parameters.values()
    except (TypeError, ValueError):
        return "positional"
    for parameter in parameters:
        if parameter.kind is Parameter.VAR_POSITIONAL:
            return "positional"
        if parameter.kind in (
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
        ):
            return "positional"
        if parameter.kind is Parameter.KEYWORD_ONLY and parameter.name == "market":
            return "keyword"
    return "none"


def _source_id_for(entries: tuple[_DataSourceEntry, ...], source: object) -> str:
    for entry in entries:
        if entry.source is source:
            return entry.source_id
    raise SlotConfigurationError("data source is not registered")
