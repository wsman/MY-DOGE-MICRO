"""Client-safe error payloads for persisted runtime traces."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class SafeError:
    code: str
    public_message: str
    internal_reference: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("SafeError.code must not be blank")
        if not self.public_message.strip():
            raise ValueError("SafeError.public_message must not be blank")
        if not self.internal_reference.strip():
            raise ValueError("SafeError.internal_reference must not be blank")

    @classmethod
    def create(cls, code: str, public_message: str) -> "SafeError":
        return cls(
            code=code,
            public_message=public_message,
            internal_reference=f"err-{uuid4().hex[:12]}",
        )

    def to_event_payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.public_message,
            "internal_reference": self.internal_reference,
        }


def safe_error_payload(code: str, public_message: str) -> dict[str, str]:
    return SafeError.create(code, public_message).to_event_payload()
