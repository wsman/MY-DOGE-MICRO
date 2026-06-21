from doge.core.ports.vector_store import VectorRecord
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore


def test_sqlite_vector_store_returns_nearest_records(tmp_path):
    store = SQLiteVectorStore(tmp_path / "agent_state.db")
    store.upsert([
        VectorRecord(
            record_id="a",
            vector=[1.0, 0.0],
            text="semiconductor demand",
            metadata={"document_id": "doc-a", "visibility": "local"},
        ),
        VectorRecord(
            record_id="b",
            vector=[0.0, 1.0],
            text="retail sales",
            metadata={"document_id": "doc-b", "visibility": "local"},
        ),
    ])

    results = store.search([1.0, 0.0], top_k=1)

    assert results[0].record.record_id == "a"
    assert results[0].score == 1.0


def test_sqlite_vector_store_applies_metadata_filter(tmp_path):
    store = SQLiteVectorStore(tmp_path / "agent_state.db")
    store.upsert([
        VectorRecord("a", [1.0], "alpha", {"document_id": "doc-a"}),
        VectorRecord("b", [1.0], "beta", {"document_id": "doc-b"}),
    ])

    results = store.search([1.0], top_k=5, metadata_filter={"document_id": "doc-b"})

    assert [result.record.record_id for result in results] == ["b"]
