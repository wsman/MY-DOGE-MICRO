"""Port for TDX server directory and connectivity checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TDXServer:
    host: str
    port: int
    latency_ms: int | None = None
    ok: bool | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        payload = {
            "host": self.host,
            "port": self.port,
            "latency_ms": self.latency_ms,
        }
        if self.ok is not None:
            payload["ok"] = self.ok
        if self.error is not None:
            payload["error"] = self.error
        return payload


class ITDXServerList(Protocol):
    """Read configured TDX servers and test individual endpoints."""

    def list_servers(self, market: str) -> list[TDXServer]:
        ...

    def test_server(self, host: str, market: str) -> TDXServer:
        ...
