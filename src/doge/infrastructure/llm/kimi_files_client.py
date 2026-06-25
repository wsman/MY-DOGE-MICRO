"""Kimi Files API adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from doge.config import get_settings
from doge.core.ports.secrets import ISecretProvider
from doge.infrastructure.secrets import EnvSecretProvider


class KimiFilesClient:
    """Small synchronous adapter around Moonshot/Kimi file APIs."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        secret_provider: ISecretProvider | None = None,
    ) -> None:
        settings = get_settings().kimi
        secrets = secret_provider or EnvSecretProvider()
        self._api_key = api_key if api_key is not None else (secrets.get_secret("kimi.api_key") or settings.api_key)
        self._base_url = base_url if base_url is not None else settings.effective_base_url()
        self._default_headers = settings.default_http_headers()
        self._supports_files_api = not _is_coding_endpoint(self._base_url, settings.coding_base_url)

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def supports_files_api(self) -> bool:
        return self._supports_files_api

    def upload_file(self, path: Path, *, purpose: str = "file-extract") -> str:
        self._require_files_api()
        client = self._client()
        with Path(path).open("rb") as handle:
            file_object = client.files.create(file=handle, purpose=purpose)
        return file_object.id

    def get_file_content(self, file_id: str) -> str:
        self._require_files_api()
        client = self._client()
        response = client.files.content(file_id)
        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text
        if callable(text):
            return text()
        return str(response)

    def get_file_info(self, file_id: str) -> dict:
        self._require_files_api()
        client = self._client()
        response = client.files.retrieve(file_id)
        if hasattr(response, "model_dump"):
            return response.model_dump(exclude_none=True)
        return dict(response)

    def delete_file(self, file_id: str) -> None:
        self._require_files_api()
        client = self._client()
        client.files.delete(file_id)

    def _require_files_api(self) -> None:
        if not self._supports_files_api:
            raise RuntimeError("Kimi Coding endpoint does not support the Files API")

    def _client(self):
        if not self._api_key:
            raise RuntimeError("MOONSHOT_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - installed in normal envs
            raise RuntimeError("openai package is not installed") from exc
        return OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            default_headers=self._default_headers or None,
        )


def _is_coding_endpoint(base_url: str, coding_base_url: str) -> bool:
    normalized = base_url.rstrip("/").lower()
    coding = coding_base_url.rstrip("/").lower()
    return normalized == coding or normalized.endswith("/coding/v1")
