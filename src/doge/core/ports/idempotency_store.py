"""Idempotency-store port for agent queue submissions."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IIdempotencyStore(ABC):
    @abstractmethod
    def get(self, key: str, scope: str) -> str | None:
        ...

    @abstractmethod
    def set(self, key: str, scope: str, run_id: str) -> None:
        ...
