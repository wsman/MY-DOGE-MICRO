"""Run models and errors for the Python SDK."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator

import httpx

from doge_sdk._utils import redact_message, response_error_message
from doge_sdk.run_models import Run, RunEvent, RunListItem


class DogeApiError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DogeEvent:
    id: str | None
    type: str
    data: dict[str, Any]


class RunsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    def list(self, limit: int = 20, session_id: str | None = None) -> list[RunListItem]:
        params: dict[str, Any] = {"limit": limit}
        if session_id is not None:
            params["session_id"] = session_id
        payload = self._root._request("GET", "/v1/runs", params=params)
        return [RunListItem(item) for item in payload["runs"]]

    def get(self, run_id: str) -> Run:
        return Run(self._root._request("GET", f"/v1/runs/{run_id}"))

    def summary(self, run_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/runs/{run_id}/summary")["summary"]

    def claims(self, run_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/runs/{run_id}/claims")["claims"]

    def citations(self, run_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/runs/{run_id}/citations")["citations"]

    def evaluation(self, run_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/runs/{run_id}/eval")["eval"]

    def events(self, run_id: str, after_sequence: int = 0) -> list[RunEvent]:
        payload = self._root._request(
            "GET",
            f"/v1/runs/{run_id}/events",
            params={"after_sequence": after_sequence},
        )
        return [RunEvent(item) for item in payload["events"]]

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
                from doge_sdk.streaming import iter_sse

                with self._root._client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
                    if response.status_code >= 400:
                        response.read()
                        message = response_error_message(response)
                        raise DogeApiError(response.status_code, redact_message(message, self._root._api_token))
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

    def approve(self, run_id: str, approval_id: str, approved: bool = True) -> Run:
        return Run(
            self._root._request(
                "POST",
                f"/v1/runs/{run_id}/approvals/{approval_id}",
                json={"approved": approved},
            )
        )

    def resume(
        self,
        run_id: str,
        approval_id: str | None = None,
        approved: bool = True,
    ) -> Run:
        payload: dict[str, Any] = {"approved": approved}
        if approval_id is not None:
            payload["approval_id"] = approval_id
        return Run(
            self._root._request(
                "POST",
                f"/v1/runs/{run_id}/resume",
                json=payload,
            )
        )

    def cancel(self, run_id: str) -> Run:
        return Run(self._root._request("POST", f"/v1/runs/{run_id}/cancel"))


class AsyncRunsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    async def list(self, limit: int = 20, session_id: str | None = None) -> list[RunListItem]:
        params: dict[str, Any] = {"limit": limit}
        if session_id is not None:
            params["session_id"] = session_id
        payload = await self._root._request("GET", "/v1/runs", params=params)
        return [RunListItem(item) for item in payload["runs"]]

    async def get(self, run_id: str) -> Run:
        return Run(await self._root._request("GET", f"/v1/runs/{run_id}"))

    async def summary(self, run_id: str) -> dict[str, Any]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/summary"))["summary"]

    async def claims(self, run_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/claims"))["claims"]

    async def citations(self, run_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/citations"))["citations"]

    async def evaluation(self, run_id: str) -> dict[str, Any]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/eval"))["eval"]

    async def events(self, run_id: str, after_sequence: int = 0) -> list[RunEvent]:
        payload = await self._root._request(
            "GET",
            f"/v1/runs/{run_id}/events",
            params={"after_sequence": after_sequence},
        )
        return [RunEvent(item) for item in payload["events"]]

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
                from doge_sdk.streaming import aiter_sse

                async with self._root._client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        message = response_error_message(response)
                        raise DogeApiError(response.status_code, redact_message(message, self._root._api_token))
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

    async def approve(self, run_id: str, approval_id: str, approved: bool = True) -> Run:
        return Run(
            await self._root._request(
                "POST",
                f"/v1/runs/{run_id}/approvals/{approval_id}",
                json={"approved": approved},
            )
        )

    async def resume(
        self,
        run_id: str,
        approval_id: str | None = None,
        approved: bool = True,
    ) -> Run:
        payload: dict[str, Any] = {"approved": approved}
        if approval_id is not None:
            payload["approval_id"] = approval_id
        return Run(
            await self._root._request(
                "POST",
                f"/v1/runs/{run_id}/resume",
                json=payload,
            )
        )

    async def cancel(self, run_id: str) -> Run:
        return Run(await self._root._request("POST", f"/v1/runs/{run_id}/cancel"))
