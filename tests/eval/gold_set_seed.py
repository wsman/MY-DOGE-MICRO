"""Deterministic fixture seeding for the financial gold-set benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import ChunkingService, PageExtractionService
from doge.core.domain.evidence_models import EvidenceRecord
from doge.infrastructure.database.agent_repositories import SQLiteDocumentRepository
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.shared.scope import TenantScope


@dataclass(frozen=True)
class SeededEvidence:
    """Evidence metadata seeded from one gold-set citation label."""

    evidence_id: str
    case_id: str
    claim_id: str | None
    document_id: str
    page_number: int
    chunk_id: str
    text: str
    support_status: str

    def to_lookup_result(self) -> dict[str, Any]:
        """Return a runtime tool result payload without LLM-sensitive content."""

        return {
            "evidence_id": self.evidence_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "text": f"Gold-set evidence reference {self.evidence_id}.",
        }


@dataclass(frozen=True)
class SeededGoldSet:
    """Indexed records produced by seeding the local benchmark database."""

    cases: list[dict[str, Any]]
    evidence_by_case: dict[str, list[SeededEvidence]]
    evidence_by_id: dict[str, SeededEvidence]
    document_ids: list[str]


def seed_gold_set(
    *,
    cases: list[dict[str, Any]],
    db_path: Path,
    storage_dir: Path,
    scope: TenantScope | None = None,
) -> SeededGoldSet:
    """Seed documents, pages, chunks, and exact evidence IDs for all cases."""

    scope = scope or TenantScope.local()
    storage_dir.mkdir(parents=True, exist_ok=True)
    document_repository = SQLiteDocumentRepository(db_path)
    evidence_repository = SQLiteEvidenceRepository(db_path)
    extraction_service = PageExtractionService(
        evidence_repository=evidence_repository,
        chunking_service=ChunkingService(chunk_size=10000, overlap=0),
    )
    upload_service = FileUploadService(
        document_repository,
        storage_dir=storage_dir,
        extraction_service=extraction_service,
    )

    document_specs = _document_specs(cases)
    page_text_by_document = _page_text_by_document(cases)
    for document_id, filename in sorted(document_specs.items()):
        content = _document_content(document_id, page_text_by_document.get(document_id, {}))
        upload_service.register_text(
            filename=filename,
            content=content,
            document_id=document_id,
            scope=scope,
        )

    evidence_by_case: dict[str, list[SeededEvidence]] = {case["id"]: [] for case in cases}
    evidence_by_id: dict[str, SeededEvidence] = {}
    chunks_by_document_page = _chunks_by_document_page(
        evidence_repository,
        sorted(document_specs),
        scope,
    )
    for case in cases:
        claims = case.get("expected_claims", [])
        claim = claims[0] if claims else {}
        support_status = str(claim.get("expected_status") or "supported")
        for citation in case.get("expected_citations", []):
            document_id = citation["document_id"]
            page_number = int(citation["page_number"])
            chunk = chunks_by_document_page[(document_id, page_number)]
            evidence_id = citation["evidence_id"]
            text = _evidence_text(case, citation)
            record = EvidenceRecord(
                evidence_id=evidence_id,
                document_id=document_id,
                page_id=chunk.page_id,
                chunk_id=chunk.chunk_id,
                page_number=page_number,
                claim=str(claim.get("text") or ""),
                support_snippet=text,
                relevance_score=1.0,
                metadata={
                    "case_id": case["id"],
                    "claim_id": claim.get("claim_id"),
                    "support_status": support_status,
                    "source": "gold_set_seed",
                },
            )
            evidence_repository.save_evidence(record, scope)
            seeded = SeededEvidence(
                evidence_id=evidence_id,
                case_id=case["id"],
                claim_id=claim.get("claim_id"),
                document_id=document_id,
                page_number=page_number,
                chunk_id=chunk.chunk_id,
                text=text,
                support_status=support_status,
            )
            evidence_by_case[case["id"]].append(seeded)
            evidence_by_id[evidence_id] = seeded

    _assert_seed_coverage(cases, evidence_by_id)
    return SeededGoldSet(
        cases=cases,
        evidence_by_case=evidence_by_case,
        evidence_by_id=evidence_by_id,
        document_ids=sorted(document_specs),
    )


def _document_specs(cases: list[dict[str, Any]]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for case in cases:
        for material in case.get("materials", []):
            document_id = material["document_id"]
            specs.setdefault(document_id, material.get("filename") or f"{document_id}.txt")
    return specs


def _page_text_by_document(cases: list[dict[str, Any]]) -> dict[str, dict[int, list[str]]]:
    pages: dict[str, dict[int, list[str]]] = {}
    for case in cases:
        for citation in case.get("expected_citations", []):
            document_id = citation["document_id"]
            page_number = int(citation["page_number"])
            pages.setdefault(document_id, {}).setdefault(page_number, []).append(
                _evidence_text(case, citation)
            )
    for case in cases:
        for material in case.get("materials", []):
            document_id = material["document_id"]
            pages.setdefault(document_id, {}).setdefault(
                1,
                [f"{document_id} deterministic benchmark fixture."],
            )
    return pages


def _document_content(document_id: str, pages: dict[int, list[str]]) -> str:
    max_page = max(pages) if pages else 1
    parts: list[str] = []
    for page_number in range(1, max_page + 1):
        lines = pages.get(page_number) or [
            f"{document_id} benchmark filler page {page_number}."
        ]
        parts.append("\n".join(lines))
    return "\f".join(parts)


def _evidence_text(case: dict[str, Any], citation: dict[str, Any]) -> str:
    claims = case.get("expected_claims", [])
    claim_text = str(claims[0].get("text") if claims else case["question"])
    number_parts = [
        f"{item['metric']}={item['value']}"
        for item in case.get("expected_numbers", [])
    ]
    numbers = "; ".join(number_parts) if number_parts else "no numeric label"
    return (
        f"{citation['evidence_id']} supports benchmark case {case['id']}. "
        f"Claim label: {claim_text} "
        f"Numeric labels: {numbers}."
    )


def _chunks_by_document_page(
    evidence_repository: SQLiteEvidenceRepository,
    document_ids: list[str],
    scope: TenantScope,
):
    chunks = evidence_repository.list_chunks(scope, document_ids, limit=10000)
    by_key = {}
    for chunk in chunks:
        by_key[(chunk.document_id, chunk.page_number)] = chunk
    return by_key


def _assert_seed_coverage(cases: list[dict[str, Any]], evidence_by_id: dict[str, SeededEvidence]) -> None:
    expected_ids = {
        citation["evidence_id"]
        for case in cases
        for citation in case.get("expected_citations", [])
    }
    missing = sorted(expected_ids - set(evidence_by_id))
    if missing:
        raise AssertionError(f"missing seeded evidence IDs: {', '.join(missing)}")
