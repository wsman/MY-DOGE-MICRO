from types import SimpleNamespace

import openai
import pytest

from doge.infrastructure.llm.kimi_files_client import KimiFilesClient


class _SecretProvider:
    def __init__(self, values):
        self.values = values

    def get_secret(self, name: str):
        return self.values.get(name)


def test_kimi_files_client_uploads_and_reads_content(monkeypatch, tmp_path):
    captured = {}

    class FakeFiles:
        def create(self, *, file, purpose):
            captured["filename"] = file.name
            captured["purpose"] = purpose
            return SimpleNamespace(id="file-123")

        def content(self, file_id):
            captured["content_file_id"] = file_id
            return SimpleNamespace(text="extracted text")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.files = FakeFiles()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF fake")

    client = KimiFilesClient(api_key="moonshot-key", base_url="https://api.moonshot.ai/v1")

    file_id = client.upload_file(source)
    content = client.get_file_content(file_id)

    assert file_id == "file-123"
    assert content == "extracted text"
    assert captured["client"]["api_key"] == "moonshot-key"
    assert captured["client"]["base_url"] == "https://api.moonshot.ai/v1"
    assert captured["purpose"] == "file-extract"
    assert captured["content_file_id"] == "file-123"


def test_kimi_files_client_reads_key_from_secret_provider(monkeypatch, tmp_path):
    captured = {}

    class FakeFiles:
        def create(self, *, file, purpose):
            return SimpleNamespace(id="file-123")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.files = FakeFiles()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    source = tmp_path / "report.txt"
    source.write_text("fixture", encoding="utf-8")

    client = KimiFilesClient(secret_provider=_SecretProvider({"kimi.api_key": "provider-key"}))

    assert client.upload_file(source) == "file-123"
    assert captured["client"]["api_key"] == "provider-key"


def test_kimi_files_client_fails_safely_without_key():
    client = KimiFilesClient(api_key="")

    with pytest.raises(RuntimeError, match="MOONSHOT_API_KEY"):
        client.get_file_content("file-123")
