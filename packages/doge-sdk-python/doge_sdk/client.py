"""Synchronous Python SDK client for the v1 daemon API."""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator
from uuid import uuid4

import httpx

from doge_sdk.run import DogeApiError, DogeEvent
from doge_sdk.session import AsyncSession, Session
from doge_sdk.streaming import aiter_sse, iter_sse


class DogeClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8901",
        api_token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.sessions = SessionsResource(self)
        self.runs = RunsResource(self)
        self.documents = DocumentsResource(self)

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message") or payload.get("detail") or response.text
            except Exception:
                message = response.text
            raise DogeApiError(response.status_code, message)
        return response.json()


class SessionsResource:
    def __init__(self, root: DogeClient) -> None:
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


class RunsResource:
    def __init__(self, root: DogeClient) -> None:
        self._root = root

    def get(self, run_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/runs/{run_id}")

    def events(self, run_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        return self._root._request(
            "GET",
            f"/v1/runs/{run_id}/events",
            params={"after_sequence": after_sequence},
        )["events"]

    def stream(
        self,
        run_id: str,
        last_event_id: str | None = None,
        *,
        reconnect: bool = True,
        max_reconnects: int = 3,
        backoff_seconds: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> Iterator[DogeEvent]:
        attempts = 0
        while True:
            headers = {"Last-Event-ID": last_event_id} if last_event_id else None
            try:
                with self._root._client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
                    if response.status_code >= 400:
                        raise DogeApiError(response.status_code, response.text)
                    for event in iter_sse(response):
                        if event.id:
                            last_event_id = event.id
                        attempts = 0
                        yield event
                return
            except httpx.HTTPError:
                if not reconnect or attempts >= max_reconnects:
                    raise
                attempts += 1
                sleep(backoff_seconds * attempts)

    def approve(self, run_id: str, approval_id: str, approved: bool = True) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/runs/{run_id}/approvals/{approval_id}",
            json={"approved": approved},
        )

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self._root._request("POST", f"/v1/runs/{run_id}/cancel")


class DocumentsResource:
    def __init__(self, root: DogeClient) -> None:
        self._root = root

    def create(self, filename: str, content: str = "") -> dict[str, Any]:
        return self._root._request("POST", "/v1/documents", json={"filename": filename, "content": content})

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/documents", params={"limit": limit})["documents"]

    def get(self, document_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/documents/{document_id}")


class AsyncDogeClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8901",
        api_token: str | None = None,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.sessions = AsyncSessionsResource(self)
        self.runs = AsyncRunsResource(self)
        self.documents = AsyncDocumentsResource(self)

    async def __aenter__(self) -> "AsyncDogeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message") or payload.get("detail") or response.text
            except Exception:
                message = response.text
            raise DogeApiError(response.status_code, message)
        return response.json()


class AsyncSessionsResource:
    def __init__(self, root: AsyncDogeClient) -> None:
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


class AsyncRunsResource:
    def __init__(self, root: AsyncDogeClient) -> None:
        self._root = root

    async def get(self, run_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/runs/{run_id}")

    async def events(self, run_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        return (await self._root._request(
            "GET",
            f"/v1/runs/{run_id}/events",
            params={"after_sequence": after_sequence},
        ))["events"]

    async def stream(
        self,
        run_id: str,
        last_event_id: str | None = None,
        *,
        reconnect: bool = True,
        max_reconnects: int = 3,
        backoff_seconds: float = 0.25,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> AsyncIterator[DogeEvent]:
        attempts = 0
        while True:
            headers = {"Last-Event-ID": last_event_id} if last_event_id else None
            try:
                async with self._root._client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
                    if response.status_code >= 400:
                        raise DogeApiError(response.status_code, response.text)
                    async for event in aiter_sse(response):
                        if event.id:
                            last_event_id = event.id
                        attempts = 0
                        yield event
                return
            except httpx.HTTPError:
                if not reconnect or attempts >= max_reconnects:
                    raise
                attempts += 1
                await sleep(backoff_seconds * attempts)

    async def approve(self, run_id: str, approval_id: str, approved: bool = True) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/runs/{run_id}/approvals/{approval_id}",
            json={"approved": approved},
        )

    async def cancel(self, run_id: str) -> dict[str, Any]:
        return await self._root._request("POST", f"/v1/runs/{run_id}/cancel")


class AsyncDocumentsResource:
    def __init__(self, root: AsyncDogeClient) -> None:
        self._root = root

    async def create(self, filename: str, content: str = "") -> dict[str, Any]:
        return await self._root._request("POST", "/v1/documents", json={"filename": filename, "content": content})

    async def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return (await self._root._request("GET", "/v1/documents", params={"limit": limit}))["documents"]

    async def get(self, document_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/documents/{document_id}")
