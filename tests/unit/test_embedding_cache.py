from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider


def test_hashing_embedding_provider_is_deterministic():
    provider = HashingEmbeddingProvider(dimensions=8)

    first = provider.embed_texts(["semiconductor outlook"])[0]
    second = provider.embed_texts(["semiconductor outlook"])[0]

    assert first == second
    assert len(first) == 8


def test_sqlite_embedding_cache_round_trips_vectors(tmp_path):
    cache = SQLiteEmbeddingCache(tmp_path / "agent_state.db")

    cache.set("key-1", [0.1, 0.2, 0.3])

    assert cache.get("key-1") == [0.1, 0.2, 0.3]
    assert cache.get("missing") is None
