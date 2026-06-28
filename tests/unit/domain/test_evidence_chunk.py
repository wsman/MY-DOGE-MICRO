"""Unit tests for the EvidenceChunk domain model."""

from doge.core.domain.evidence_chunk_models import EvidenceChunk, _stable_evidence_id


def test_evidence_chunk_create_generates_stable_id():
    """Creating two EvidenceChunks with identical fields should yield the same evidence_id."""
    chunk_a = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 15% year over year.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    chunk_b = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 15% year over year.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    assert chunk_a.evidence_id == chunk_b.evidence_id
    assert chunk_a.evidence_id.startswith("evd-")


def test_evidence_chunk_create_different_fields_different_id():
    """Different field values should produce different evidence_ids."""
    chunk_a = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 15%.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    chunk_b = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 16%.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    assert chunk_a.evidence_id != chunk_b.evidence_id


def test_evidence_chunk_fields_populated():
    """All required fields should be present and correct."""
    chunk = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 15% year over year.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    assert chunk.document_id == "doc-1"
    assert chunk.page_number == 3
    assert chunk.chunk_id == "chunk-42"
    assert chunk.text == "Revenue grew by 15% year over year."
    assert chunk.source_tool == "financial_scanner"
    assert chunk.run_id == "run-7"
    assert chunk.created_at is not None


def test_evidence_chunk_frozen_immutable():
    """EvidenceChunk should be frozen (immutable)."""
    chunk = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew.",
        source_tool="scanner",
        run_id="run-7",
    )
    try:
        chunk.text = "modified"
        raise AssertionError("Expected FrozenInstanceError")
    except Exception as e:
        assert "frozen" in str(e).lower() or "cannot assign" in str(e).lower()


def test_evidence_chunk_to_dict_roundtrip():
    """to_dict and from_mapping should be inverse operations."""
    original = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew by 15% year over year.",
        source_tool="financial_scanner",
        run_id="run-7",
    )
    data = original.to_dict()
    restored = EvidenceChunk.from_mapping(data)
    assert original == restored


def test_evidence_chunk_from_mapping_with_defaults():
    """from_mapping should handle missing optional fields with defaults."""
    data = {
        "evidence_id": "evd-abc123",
        "document_id": "doc-1",
        "page_number": "3",
        "chunk_id": "chunk-42",
        "text": "Revenue grew.",
        "source_tool": "scanner",
    }
    chunk = EvidenceChunk.from_mapping(data)
    assert chunk.evidence_id == "evd-abc123"
    assert chunk.document_id == "doc-1"
    assert chunk.page_number == 3
    assert chunk.chunk_id == "chunk-42"
    assert chunk.text == "Revenue grew."
    assert chunk.source_tool == "scanner"
    assert chunk.run_id is None
    assert chunk.created_at is not None


def test_evidence_chunk_run_id_optional():
    """EvidenceChunk should be creatable without a run_id."""
    chunk = EvidenceChunk.create(
        document_id="doc-1",
        page_number=3,
        chunk_id="chunk-42",
        text="Revenue grew.",
        source_tool="scanner",
    )
    assert chunk.run_id is None
    assert chunk.evidence_id.startswith("evd-")


def test_stable_evidence_id_format():
    """_stable_evidence_id should produce a string starting with 'evd-'."""
    eid = _stable_evidence_id("run-1", "doc-1", "chunk-1", "tool", "text")
    assert eid.startswith("evd-")
    assert len(eid) == 20  # "evd-" + 16 hex chars
