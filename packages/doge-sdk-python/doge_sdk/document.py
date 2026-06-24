"""Document resources for the Python SDK."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DocumentsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    def create(self, filename: str, content: str = "") -> dict[str, Any]:
        return self._root._request("POST", "/v1/documents", json={"filename": filename, "content": content})

    def upload_bytes(
        self,
        filename: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self._root._request(
            "POST",
            "/v1/documents",
            files={"file": (filename, payload, content_type)},
        )

    def upload_path(self, path: str | Path, *, content_type: str = "application/octet-stream") -> dict[str, Any]:
        source = Path(path)
        return self.upload_bytes(source.name, source.read_bytes(), content_type=content_type)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._root._request("GET", "/v1/documents", params={"limit": limit})["documents"]

    def get(self, document_id: str) -> dict[str, Any]:
        return self._root._request("GET", f"/v1/documents/{document_id}")


class AsyncDocumentsResource:
    def __init__(self, root: Any) -> None:
        self._root = root

    async def create(self, filename: str, content: str = "") -> dict[str, Any]:
        return await self._root._request("POST", "/v1/documents", json={"filename": filename, "content": content})

    async def upload_bytes(
        self,
        filename: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return await self._root._request(
            "POST",
            "/v1/documents",
            files={"file": (filename, payload, content_type)},
        )

    async def upload_path(self, path: str | Path, *, content_type: str = "application/octet-stream") -> dict[str, Any]:
        source = Path(path)
        return await self.upload_bytes(source.name, source.read_bytes(), content_type=content_type)

    async def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return (await self._root._request("GET", "/v1/documents", params={"limit": limit}))["documents"]

    async def get(self, document_id: str) -> dict[str, Any]:
        return await self._root._request("GET", f"/v1/documents/{document_id}")
