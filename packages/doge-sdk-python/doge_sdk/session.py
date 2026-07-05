"""Session resource wrapper."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


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
        workflow: str | None = None,
        **kwargs: Any,
    ) -> str:
        policy = dict(model_policy or {})
        policy.setdefault("execution_profile", execution_profile)
        if workflow is not None:
            kwargs["workflow"] = workflow
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
        workflow: str | None = None,
        **kwargs: Any,
    ) -> str:
        policy = dict(model_policy or {})
        policy.setdefault("execution_profile", execution_profile)
        if workflow is not None:
            kwargs["workflow"] = workflow
        return await self.create_turn(question, model_policy=policy, **kwargs)


class SessionsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    def create(self, title: str = "Research session") -> Session:
        return Session(self._root, self._root._request("POST", "/v1/sessions", json={"title": title}))

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/sessions", params={"limit": limit})["sessions"]

    def get(self, session_id: str) -> Session:
        return Session(self._root, self._root._request("GET", f"/v1/sessions/{session_id}"))

    def create_turn(self, session_id: str, message: str, idempotency_key: str | None = None, **kwargs: Any) -> str:
        headers = {"Idempotency-Key": idempotency_key or str(uuid4())}
        payload = {"message": message, **kwargs}
        return self._root._request(
            "POST",
            f"/v1/sessions/{session_id}/turns",
            json=payload,
            headers=headers,
        )["run_id"]


class AsyncSessionsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    async def create(self, title: str = "Research session") -> AsyncSession:
        payload = await self._root._request("POST", "/v1/sessions", json={"title": title})
        return AsyncSession(self._root, payload)

    async def list(self, limit: int = 20) -> list[dict[str, Any]]:
        return (await self._root._request("GET", "/v1/sessions", params={"limit": limit}))["sessions"]

    async def get(self, session_id: str) -> AsyncSession:
        return AsyncSession(self._root, await self._root._request("GET", f"/v1/sessions/{session_id}"))

    async def create_turn(
        self,
        session_id: str,
        message: str,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> str:
        headers = {"Idempotency-Key": idempotency_key or str(uuid4())}
        payload = {"message": message, **kwargs}
        return (await self._root._request(
            "POST",
            f"/v1/sessions/{session_id}/turns",
            json=payload,
            headers=headers,
        ))["run_id"]
