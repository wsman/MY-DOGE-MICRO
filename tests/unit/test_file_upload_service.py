from pathlib import Path

import pytest

from doge.application.services.file_upload_service import FileUploadError, FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository


class FakeParser:
    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        return Path(path).read_text(encoding="utf-8")[:max_chars]


def test_register_path_persists_hash_mime_size_and_content(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "report.txt"
    source.write_text("alpha beta", encoding="utf-8")
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=FakeParser(),
    )

    document = service.register_path(source)

    assert document["document_id"].startswith("doc-")
    assert document["filename"] == "report.txt"
    assert document["original_filename"] == "report.txt"
    assert document["file_hash"]
    assert document["mime_type"] == "text/plain"
    assert document["size_bytes"] == len("alpha beta")
    assert document["parsing_status"] == "parsed"
    assert document["content"] == "alpha beta"
    assert Path(document["storage_path"]).exists()


def test_register_path_is_idempotent_by_hash(tmp_path):
    db = tmp_path / "agent_state.db"
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("same payload", encoding="utf-8")
    second.write_text("same payload", encoding="utf-8")
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=FakeParser(),
    )

    first_doc = service.register_path(first)
    second_doc = service.register_path(second)

    assert second_doc["document_id"] == first_doc["document_id"]
    assert SQLiteDocumentRepository(db).list_recent() == [first_doc]


def test_register_path_optionally_extracts_pages_and_chunks(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "report.txt"
    source.write_text("alpha beta", encoding="utf-8")
    evidence = SQLiteEvidenceRepository(db)
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=FakeParser(),
        extraction_service=PageExtractionService(evidence_repository=evidence),
    )

    document = service.register_path(source)

    chunks = evidence.list_chunks([document["document_id"]], limit=5)
    assert chunks[0].text == "alpha beta"


def test_register_rejects_unsupported_type(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "payload.exe"
    source.write_bytes(b"nope")
    service = FileUploadService(SQLiteDocumentRepository(db), storage_dir=tmp_path / "documents")

    with pytest.raises(FileUploadError, match="unsupported file type"):
        service.register_path(source)


def test_register_text_preserves_json_compatibility(tmp_path):
    db = tmp_path / "agent_state.db"
    service = FileUploadService(SQLiteDocumentRepository(db), storage_dir=tmp_path / "documents")

    document = service.register_text(filename="note.md", content="# memo", document_id="doc-custom")

    assert document["document_id"] == "doc-custom"
    assert document["filename"] == "note.md"
    assert document["file_hash"]
    assert document["size_bytes"] == len("# memo")
    assert document["parsing_status"] == "parsed"
    assert document["content"] == "# memo"
