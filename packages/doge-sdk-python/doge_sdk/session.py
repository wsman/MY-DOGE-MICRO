"""Session resource wrapper."""

from __future__ import annotations

from typing import Any


class Session:
    def __init__(self, client: Any, data: dict[str, Any]) -> None:
        self._client = client
        self.data = data
        self.session_id = data["session_id"]

    def create_turn(self, message: str, **kwargs: Any) -> str:
        return self._client.sessions.create_turn(self.session_id, message, **kwargs)

    def run(
        self,
        question: str,
        *,
        execution_profile: str = "financial_research",
        model_policy: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        policy = dict(model_policy or {})
        policy.setdefault("execution_profile", execution_profile)
        return self.create_turn(question, model_policy=policy, **kwargs)


class AsyncSession(Session):
    async def create_turn(self, message: str, **kwargs: Any) -> str:
        return await self._client.sessions.create_turn(self.session_id, message, **kwargs)

    async def run(
        self,
        question: str,
        *,
        execution_profile: str = "financial_research",
        model_policy: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        policy = dict(model_policy or {})
        policy.setdefault("execution_profile", execution_profile)
        return await self.create_turn(question, model_policy=policy, **kwargs)
