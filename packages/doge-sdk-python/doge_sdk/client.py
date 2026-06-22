"""Synchronous Python SDK client for the v1 daemon API."""

from __future__ import annotations

import asyncio
import re
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
        request_id: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_token = api_token
        headers = _client_headers(api_token, request_id)
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.sessions = SessionsResource(self)
        self.runs = RunsResource(self)
        self.documents = DocumentsResource(self)
        self.platform = PlatformResource(self)
        self.capabilities = CapabilitiesResource(self)

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
            raise DogeApiError(response.status_code, _redact_message(message, self._api_token))
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

    def summary(self, run_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/runs/{run_id}/summary")["summary"]

    def claims(self, run_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/runs/{run_id}/claims")["claims"]

    def citations(self, run_id: str) -> list[dict[str, Any]]:
        return self._root._request("GET", f"/v1/runs/{run_id}/citations")["citations"]

    def evaluation(self, run_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/runs/{run_id}/eval")["eval"]

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
                        response.read()
                        message = _response_error_message(response)
                        raise DogeApiError(response.status_code, _redact_message(message, self._root._api_token))
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


class PlatformResource:
    def __init__(self, root: DogeClient) -> None:
        self._root = root

    def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/workspaces", params={"limit": limit})["workspaces"]

    def create_workspace(self, name: str, description: str = "") -> dict[str, Any]:
        return self._root._request("POST", "/v1/workspaces", json={"name": name, "description": description})

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/workspaces/{workspace_id}")

    def list_projects(self, workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        return self._root._request("GET", "/v1/projects", params=params)["projects"]

    def create_project(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/projects",
            json={
                "workspace_id": workspace_id,
                "name": name,
                "description": description,
                "default_market": default_market,
            },
        )

    def get_project(self, project_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/projects/{project_id}")

    def list_research_cases(self, project_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if project_id is not None:
            params["project_id"] = project_id
        return self._root._request("GET", "/v1/research-cases", params=params)["research_cases"]

    def create_research_case(self, project_id: str, title: str, thesis: str = "") -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/research-cases",
            json={"project_id": project_id, "title": title, "thesis": thesis},
        )

    def get_research_case(self, case_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/research-cases/{case_id}")

    def link_research_case_run(self, case_id: str, run_id: str, link_type: str = "primary") -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={"run_id": run_id, "link_type": link_type},
        )

    def create_research_case_run_from_template(
        self,
        case_id: str,
        template_id: str,
        *,
        question: str | None = None,
        model_policy: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        workflow: str | None = None,
        session_id: str | None = None,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = None,
        link_type: str = "primary",
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={
                "template_id": template_id,
                "question": question,
                "model_policy": model_policy or {},
                "inputs": inputs or {},
                "workflow": workflow,
                "session_id": session_id,
                "market": market,
                "language": language,
                "document_ids": document_ids or [],
                "portfolio_id": portfolio_id,
                "link_type": link_type,
            },
        )

    def list_workflow_templates(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/workflow-templates", params={"limit": limit})["workflow_templates"]

    def create_workflow_template(
        self,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/workflow-templates",
            json={
                "slug": slug,
                "name": name,
                "description": description,
                "current_version": current_version,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
            },
        )

    def get_workflow_template(self, template_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/workflow-templates/{template_id}")


class CapabilitiesResource:
    def __init__(self, root: DogeClient) -> None:
        self._root = root

    def get(self) -> dict[str, Any]:
        return self._root._request("GET", "/v1/capabilities")

    def list(self) -> list[dict[str, Any]]:
        return self.get()["capabilities"]


class AsyncDogeClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8901",
        api_token: str | None = None,
        request_id: str | None = None,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_token = api_token
        headers = _client_headers(api_token, request_id)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.sessions = AsyncSessionsResource(self)
        self.runs = AsyncRunsResource(self)
        self.documents = AsyncDocumentsResource(self)
        self.platform = AsyncPlatformResource(self)
        self.capabilities = AsyncCapabilitiesResource(self)

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
            raise DogeApiError(response.status_code, _redact_message(message, self._api_token))
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

    async def summary(self, run_id: str) -> dict[str, Any]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/summary"))["summary"]

    async def claims(self, run_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/claims"))["claims"]

    async def citations(self, run_id: str) -> list[dict[str, Any]]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/citations"))["citations"]

    async def evaluation(self, run_id: str) -> dict[str, Any]:
        return (await self._root._request("GET", f"/v1/runs/{run_id}/eval"))["eval"]

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
                        await response.aread()
                        message = _response_error_message(response)
                        raise DogeApiError(response.status_code, _redact_message(message, self._root._api_token))
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


class AsyncPlatformResource:
    def __init__(self, root: AsyncDogeClient) -> None:
        self._root = root

    async def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        return (await self._root._request("GET", "/v1/workspaces", params={"limit": limit}))["workspaces"]

    async def create_workspace(self, name: str, description: str = "") -> dict[str, Any]:
        return await self._root._request("POST", "/v1/workspaces", json={"name": name, "description": description})

    async def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/workspaces/{workspace_id}")

    async def list_projects(self, workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if workspace_id is not None:
            params["workspace_id"] = workspace_id
        return (await self._root._request("GET", "/v1/projects", params=params))["projects"]

    async def create_project(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        default_market: str | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/projects",
            json={
                "workspace_id": workspace_id,
                "name": name,
                "description": description,
                "default_market": default_market,
            },
        )

    async def get_project(self, project_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/projects/{project_id}")

    async def list_research_cases(self, project_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if project_id is not None:
            params["project_id"] = project_id
        return (await self._root._request("GET", "/v1/research-cases", params=params))["research_cases"]

    async def create_research_case(self, project_id: str, title: str, thesis: str = "") -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/research-cases",
            json={"project_id": project_id, "title": title, "thesis": thesis},
        )

    async def get_research_case(self, case_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/research-cases/{case_id}")

    async def link_research_case_run(self, case_id: str, run_id: str, link_type: str = "primary") -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={"run_id": run_id, "link_type": link_type},
        )

    async def create_research_case_run_from_template(
        self,
        case_id: str,
        template_id: str,
        *,
        question: str | None = None,
        model_policy: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        workflow: str | None = None,
        session_id: str | None = None,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = None,
        link_type: str = "primary",
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            f"/v1/research-cases/{case_id}/runs",
            json={
                "template_id": template_id,
                "question": question,
                "model_policy": model_policy or {},
                "inputs": inputs or {},
                "workflow": workflow,
                "session_id": session_id,
                "market": market,
                "language": language,
                "document_ids": document_ids or [],
                "portfolio_id": portfolio_id,
                "link_type": link_type,
            },
        )

    async def list_workflow_templates(self, limit: int = 100) -> list[dict[str, Any]]:
        return (
            await self._root._request("GET", "/v1/workflow-templates", params={"limit": limit})
        )["workflow_templates"]

    async def create_workflow_template(
        self,
        slug: str,
        name: str,
        description: str = "",
        current_version: str = "1",
        input_schema: dict[str, Any] | None = None,
        run_instructions: str = "",
        tool_policy: dict[str, Any] | None = None,
        evidence_policy: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/workflow-templates",
            json={
                "slug": slug,
                "name": name,
                "description": description,
                "current_version": current_version,
                "input_schema": input_schema or {},
                "run_instructions": run_instructions,
                "tool_policy": tool_policy or {},
                "evidence_policy": evidence_policy or {},
                "output_contract": output_contract or {},
            },
        )

    async def get_workflow_template(self, template_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/workflow-templates/{template_id}")


class AsyncCapabilitiesResource:
    def __init__(self, root: AsyncDogeClient) -> None:
        self._root = root

    async def get(self) -> dict[str, Any]:
        return await self._root._request("GET", "/v1/capabilities")

    async def list(self) -> list[dict[str, Any]]:
        return (await self.get())["capabilities"]


def _client_headers(api_token: str | None, request_id: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b("
    r"api[_-]?key|password|secret|token|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|"
    r"moonshot_api_key|deepseek_api_key|doge_api_token"
    r")\s*([=:])\s*(['\"]?)[^&\s,'\"}]+",
    re.IGNORECASE,
)
_SK_PATTERN = re.compile(r"\bsk-[A-Za-z0-9._-]{6,}")


def _response_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        return payload.get("error", {}).get("message") or payload.get("detail") or response.text
    except Exception:
        return response.text


def _redact_message(message: str, api_token: str | None) -> str:
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", message)
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
    redacted = _SK_PATTERN.sub("sk-[REDACTED]", redacted)
    if api_token:
        redacted = redacted.replace(api_token, "[REDACTED]")
    return redacted
