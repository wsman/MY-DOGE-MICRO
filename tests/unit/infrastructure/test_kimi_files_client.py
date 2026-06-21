from types import SimpleNamespace

import openai
import pytest

from doge.infrastructure.llm.kimi_files_client import KimiFilesClient


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


def test_kimi_files_client_fails_safely_without_key():
    client = KimiFilesClient(api_key="")

    with pytest.raises(RuntimeError, match="MOONSHOT_API_KEY"):
        client.get_file_content("file-123")
