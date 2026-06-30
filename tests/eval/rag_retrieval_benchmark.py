"""Deterministic local RAG retrieval benchmark over the financial gold set."""

from __future__ import annotations

import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from doge.application.services.rag_service import RAGService
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore
from doge.shared.scope import TenantScope

from tests.eval.gold_eval import load_gold_cases, summarize_gold_set
from tests.eval.gold_set_runner import GOLD_CASES_PATH
from tests.eval.gold_set_seed import SeededGoldSet, seed_gold_set


def run_benchmark(
    *,
    gold_cases_path: Path = GOLD_CASES_PATH,
    db_path: Path | None = None,
    storage_dir: Path | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run deterministic RAG retrieval over all labeled gold-set cases."""

    cases = load_gold_cases(gold_cases_path)
    if db_path is not None and storage_dir is not None:
        return _run_benchmark(cases, db_path=db_path, storage_dir=storage_dir, top_k=top_k)

    with tempfile.TemporaryDirectory(prefix="doge-rag-benchmark-") as tmp:
        root = Path(tmp)
        return _run_benchmark(
            cases,
            db_path=db_path or root / "agent_state.db",
            storage_dir=storage_dir or root / "storage",
            top_k=top_k,
        )


def _run_benchmark(
    cases: list[dict[str, Any]],
    *,
    db_path: Path,
    storage_dir: Path,
    top_k: int,
) -> dict[str, Any]:
    scope = TenantScope.local()
    seeded = seed_gold_set(
        cases=cases,
        db_path=db_path,
        storage_dir=storage_dir,
        scope=scope,
    )
    service = RAGService(
        evidence_repository=SQLiteEvidenceRepository(db_path),
        embedding_provider=HashingEmbeddingProvider(),
        vector_store=SQLiteVectorStore(db_path),
        embedding_cache=SQLiteEmbeddingCache(db_path),
    )

    observations = []
    for case in cases:
        observations.append(_observe_case(case, seeded, service, scope=scope, top_k=top_k))

    metrics = _aggregate_metrics(observations)
    return {
        "schema_version": "doge.rag_retrieval_benchmark.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "local_deterministic_rag_gold_set",
        "gold_set": summarize_gold_set(cases),
        "top_k": top_k,
        "metrics": metrics,
        "observed_case_count": len(observations),
        "observations": observations,
        "external_gate_closure_allowed": False,
        "notes": [
            "This benchmark validates local deterministic RAG retrieval only.",
            "It does not close W3-live or production vector backend gates.",
        ],
    }


def _observe_case(
    case: dict[str, Any],
    seeded: SeededGoldSet,
    service: RAGService,
    *,
    scope: TenantScope,
    top_k: int,
) -> dict[str, Any]:
    expected_citations = case.get("expected_citations", [])
    expected_ids = [citation["evidence_id"] for citation in expected_citations]
    expected_count = max(1, len(expected_ids))
    document_ids = [material["document_id"] for material in case.get("materials", [])]
    result = service.search(
        _search_query(case),
        document_ids=document_ids,
        limit=max(top_k, expected_count),
        scope=scope,
    )
    retrieved_ids_at_k = _retrieved_evidence_ids(result["results"][:top_k], seeded)
    expected_chunk_ids = _expected_chunk_ids(expected_ids, seeded)
    retrieved_chunk_ids_at_expected = _retrieved_chunk_ids(result["results"][:expected_count])
    expected_set = set(expected_ids)
    return {
        "case_id": case["id"],
        "question": case["question"],
        "expected_evidence_ids": expected_ids,
        "expected_chunk_ids": expected_chunk_ids,
        "retrieved_evidence_ids_at_k": retrieved_ids_at_k,
        "retrieved_chunk_ids_at_expected": retrieved_chunk_ids_at_expected,
        "retrieval_recall_at_k": _recall(set(retrieved_ids_at_k), expected_set),
        "retrieval_precision_at_expected": _precision(
            set(retrieved_chunk_ids_at_expected),
            set(expected_chunk_ids),
        ),
        "citation_linkage": _citation_linkage(case, result["results"][:top_k]),
        "numerical_consistency": _numerical_consistency(case, result["results"][:top_k]),
        "result_count": len(result["results"]),
    }


def _search_query(case: dict[str, Any]) -> str:
    claim_text = " ".join(
        str(claim.get("text", ""))
        for claim in case.get("expected_claims", [])
        if claim.get("text")
    )
    number_text = " ".join(
        f"{item['metric']} {item['value']}"
        for item in case.get("expected_numbers", [])
    )
    return " ".join(part for part in (case["question"], claim_text, number_text) if part)


def _retrieved_evidence_ids(results: list[dict[str, Any]], seeded: SeededGoldSet) -> list[str]:
    evidence_ids_by_chunk: dict[str, list[str]] = defaultdict(list)
    for evidence in seeded.evidence_by_id.values():
        evidence_ids_by_chunk[evidence.chunk_id].append(evidence.evidence_id)
    retrieved: list[str] = []
    seen: set[str] = set()
    for result in results:
        for evidence_id in evidence_ids_by_chunk.get(str(result.get("chunk_id")), []):
            if evidence_id not in seen:
                retrieved.append(evidence_id)
                seen.add(evidence_id)
    return retrieved


def _expected_chunk_ids(expected_evidence_ids: list[str], seeded: SeededGoldSet) -> list[str]:
    chunk_ids: list[str] = []
    seen: set[str] = set()
    for evidence_id in expected_evidence_ids:
        evidence = seeded.evidence_by_id.get(evidence_id)
        if evidence is not None and evidence.chunk_id not in seen:
            chunk_ids.append(evidence.chunk_id)
            seen.add(evidence.chunk_id)
    return chunk_ids


def _retrieved_chunk_ids(results: list[dict[str, Any]]) -> list[str]:
    chunk_ids: list[str] = []
    seen: set[str] = set()
    for result in results:
        chunk_id = str(result.get("chunk_id"))
        if chunk_id and chunk_id not in seen:
            chunk_ids.append(chunk_id)
            seen.add(chunk_id)
    return chunk_ids


def _citation_linkage(case: dict[str, Any], results: list[dict[str, Any]]) -> float | None:
    expected = {
        (citation["document_id"], int(citation["page_number"]))
        for citation in case.get("expected_citations", [])
    }
    if not expected:
        return None
    observed = {
        (str(result.get("document_id")), int(result.get("page_number", 0)))
        for result in results
    }
    return len(expected & observed) / len(expected)


def _numerical_consistency(case: dict[str, Any], results: list[dict[str, Any]]) -> float | None:
    if case.get("execution_profile") == "vision_analysis":
        return None
    expected_numbers = case.get("expected_numbers", [])
    if not expected_numbers:
        return None
    result_text = "\n".join(str(result.get("text", "")) for result in results)
    matches = 0
    for item in expected_numbers:
        if f"{item['metric']}={item['value']}" in result_text:
            matches += 1
    return matches / len(expected_numbers)


def _aggregate_metrics(observations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "retrieval_recall_at_k": _average(observations, "retrieval_recall_at_k"),
        "retrieval_precision_at_expected": _average(observations, "retrieval_precision_at_expected"),
        "citation_linkage": _average(observations, "citation_linkage"),
        "numerical_consistency": _average(observations, "numerical_consistency"),
    }


def _recall(observed: set[str], expected: set[str]) -> float | None:
    if not expected:
        return None
    return len(observed & expected) / len(expected)


def _precision(observed: set[str], expected: set[str]) -> float | None:
    if not observed:
        return None if not expected else 0.0
    if not expected:
        return None
    return len(observed & expected) / len(observed)


def _average(observations: list[dict[str, Any]], key: str) -> float | None:
    values = [item[key] for item in observations if item.get(key) is not None]
    if not values:
        return None
    return sum(values) / len(values)
