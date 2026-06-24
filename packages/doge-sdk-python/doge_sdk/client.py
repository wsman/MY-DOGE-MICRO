"""Python SDK client for the v1 daemon API."""

from __future__ import annotations

from typing import Any

import httpx

from doge_sdk._utils import client_headers, redact_message, response_error_message
from doge_sdk.document import AsyncDocumentsResource, DocumentsResource
from doge_sdk.platform import (
    AsyncCapabilitiesResource,
    AsyncPlatformResource,
    CapabilitiesResource,
    PlatformResource,
)
from doge_sdk.run import AsyncRunsResource, DogeApiError, RunsResource
from doge_sdk.session import AsyncSessionsResource, SessionsResource


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
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=client_headers(api_token, request_id),
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
            raise DogeApiError(
                response.status_code,
                redact_message(response_error_message(response), self._api_token),
            )
        return response.json()


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
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=client_headers(api_token, request_id),
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
            raise DogeApiError(
                response.status_code,
                redact_message(response_error_message(response), self._api_token),
            )
        return response.json()
