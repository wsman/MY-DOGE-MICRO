from pathlib import Path

import pytest

from doge.application.services.file_upload_service import (
    FileUploadError,
    FileUploadService,
    FileUploadTooLargeError,
)
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository


class ChunkTrackingStream:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._offset = 0
        self.read_sizes = []

    def read(self, size: int = -1):
        self.read_sizes.append(size)
        if self._offset >= len(self._payload):
            return b""
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


def test_register_stream_persists_metadata_without_unbounded_read(tmp_path):
    stream = ChunkTrackingStream(b"alpha beta gamma")
    service = FileUploadService(
        SQLiteDocumentRepository(tmp_path / "agent_state.db"),
        storage_dir=tmp_path / "documents",
    )

    document = service.register_stream(stream, "large.txt", chunk_size=5)

    assert document["filename"] == "large.txt"
    assert document["size_bytes"] == len(b"alpha beta gamma")
    assert Path(document["storage_path"]).exists()
    assert stream.read_sizes
    assert all(size == 5 for size in stream.read_sizes[:-1])


def test_register_stream_over_limit_aborts_and_removes_temp_file(tmp_path):
    service = FileUploadService(
        SQLiteDocumentRepository(tmp_path / "agent_state.db"),
        storage_dir=tmp_path / "documents",
        max_file_bytes=5,
    )

    with pytest.raises(FileUploadTooLargeError):
        service.register_stream(ChunkTrackingStream(b"abcdef"), "large.txt", chunk_size=2)

    assert list((tmp_path / "documents" / ".uploads").glob("*.tmp")) == []


def test_register_stream_duplicate_hash_deletes_temp_and_returns_existing(tmp_path):
    repo = SQLiteDocumentRepository(tmp_path / "agent_state.db")
    service = FileUploadService(repo, storage_dir=tmp_path / "documents")

    first = service.register_stream(ChunkTrackingStream(b"same payload"), "first.txt", chunk_size=4)
    second = service.register_stream(ChunkTrackingStream(b"same payload"), "second.txt", chunk_size=4)

    assert second["document_id"] == first["document_id"]
    assert list((tmp_path / "documents" / ".uploads").glob("*.tmp")) == []


def test_register_path_above_threshold_does_not_call_read_bytes(tmp_path, monkeypatch):
    source = tmp_path / "large.txt"
    source.write_bytes(b"larger than threshold")
    service = FileUploadService(
        SQLiteDocumentRepository(tmp_path / "agent_state.db"),
        storage_dir=tmp_path / "documents",
        streaming_threshold_bytes=4,
    )

    def fail_read_bytes(self):
        raise AssertionError("large register_path must use stream path")

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    document = service.register_path(source)

    assert document["size_bytes"] == len(b"larger than threshold")


def test_register_stream_rejects_empty_stream(tmp_path):
    service = FileUploadService(
        SQLiteDocumentRepository(tmp_path / "agent_state.db"),
        storage_dir=tmp_path / "documents",
    )

    with pytest.raises(FileUploadError, match="file is empty"):
        service.register_stream(ChunkTrackingStream(b""), "empty.txt")
