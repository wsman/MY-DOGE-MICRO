"""Run models and errors for the Python SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DogeApiError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DogeEvent:
    id: str | None
    type: str
    data: dict[str, Any]
