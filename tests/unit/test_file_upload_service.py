from pathlib import Path

import pytest

from doge.application.services.file_upload_service import FileUploadError, FileUploadService
from doge.application.services.file_purpose_router import route_kimi_file_purpose
from doge.application.services.page_extraction_service import PageExtractionService
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.shared.scope import TenantScope


class FakeParser:
    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        return Path(path).read_text(encoding="utf-8")[:max_chars]


class FakeKimiFiles:
    supports_files_api = True

    def __init__(self):
        self.uploads = []
        self.content_calls = []

    def upload_file(self, path: Path, *, purpose: str = "file-extract") -> str:
        self.uploads.append((Path(path).name, purpose))
        return f"file-{purpose}"

    def get_file_content(self, file_id: str) -> str:
        self.content_calls.append(file_id)
        return "kimi extracted"


class FakeUnsupportedKimiFiles:
    supports_files_api = False

    def upload_file(self, path: Path, *, purpose: str = "file-extract") -> str:
        raise AssertionError("unsupported Kimi Files client must not be called")

    def get_file_content(self, file_id: str) -> str:
        raise AssertionError("unsupported Kimi Files client must not be called")


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
    assert document["kimi_file_purpose"] == "file-extract"
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
    assert document["kimi_file_purpose"] == "file-extract"


def test_register_text_uses_tenant_scope(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteDocumentRepository(db)
    service = FileUploadService(repo, storage_dir=tmp_path / "documents")
    scope = TenantScope.enterprise("tenant-a", "user-a")

    document = service.register_text(filename="note.md", content="# memo", document_id="doc-tenant", scope=scope)

    assert document["tenant_id"] == "tenant-a"
    assert repo.get("doc-tenant", scope) is not None
    assert repo.get("doc-tenant", TenantScope.enterprise("tenant-b", "user-b")) is None


def test_register_text_rejects_scope_tenant_mismatch(tmp_path):
    db = tmp_path / "agent_state.db"
    service = FileUploadService(SQLiteDocumentRepository(db), storage_dir=tmp_path / "documents")

    with pytest.raises(ValueError, match="tenant mismatch"):
        service.register_text(
            filename="note.md",
            content="# memo",
            scope=TenantScope.enterprise("tenant-a", "user-a"),
            tenant_id="tenant-b",
        )


def test_file_purpose_router_routes_by_type():
    assert route_kimi_file_purpose(filename="report.pdf", mime_type="application/pdf") == "file-extract"
    assert route_kimi_file_purpose(filename="chart.png", mime_type="image/png") == "image"
    assert route_kimi_file_purpose(filename="clip.mp4", mime_type="video/mp4") == "video"
    assert route_kimi_file_purpose(filename="eval.jsonl", mime_type="application/json") == "batch"
    assert route_kimi_file_purpose(filename="data.csv", mime_type="text/csv") == "file-extract"


def test_kimi_image_upload_does_not_request_text_content(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "chart.png"
    source.write_bytes(b"fake png")
    kimi = FakeKimiFiles()
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        kimi_files_client=kimi,
    )

    document = service.register_path(source)

    assert document["kimi_file_id"] == "file-image"
    assert document["kimi_file_purpose"] == "image"
    assert document["parsing_status"] == "uploaded"
    assert document["content"] is None
    assert kimi.uploads[0][1] == "image"
    assert kimi.content_calls == []


def test_kimi_file_extract_upload_reads_text_content(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF fake")
    kimi = FakeKimiFiles()
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        kimi_files_client=kimi,
    )

    document = service.register_path(source)

    assert document["kimi_file_purpose"] == "file-extract"
    assert document["content"] == "kimi extracted"
    assert kimi.content_calls == ["file-file-extract"]


def test_unsupported_kimi_files_client_falls_back_to_local_parser(tmp_path):
    db = tmp_path / "agent_state.db"
    source = tmp_path / "report.txt"
    source.write_text("local evidence", encoding="utf-8")
    service = FileUploadService(
        SQLiteDocumentRepository(db),
        storage_dir=tmp_path / "documents",
        parser=FakeParser(),
        kimi_files_client=FakeUnsupportedKimiFiles(),
    )

    document = service.register_path(source)

    assert document["parsing_status"] == "parsed"
    assert document["content"] == "local evidence"
    assert document["kimi_file_id"] is None
    assert document["kimi_file_purpose"] == "file-extract"
