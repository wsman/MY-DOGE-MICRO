"""SQLite repository for report claims and citations."""

from __future__ import annotations

import json
from pathlib import Path

from doge.config import get_settings
from doge.core.domain.claim_models import CitationRecord, ClaimEvidenceRelation, ClaimRecord
from doge.core.ports.claim_repository import IClaimRepository
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteClaimRepository(IClaimRepository):
    """Persist report claims and citation links in the agent database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def save_claim(self, claim: ClaimRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO claim_records(
                    claim_id, report_id, text, status, evidence_count,
                    metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    report_id = excluded.report_id,
                    text = excluded.text,
                    status = excluded.status,
                    evidence_count = excluded.evidence_count,
                    metadata = excluded.metadata
                """,
                (
                    claim.claim_id,
                    claim.report_id,
                    claim.text,
                    claim.status,
                    claim.evidence_count,
                    json.dumps(claim.metadata, ensure_ascii=False),
                    claim.created_at,
                ),
            )
            conn.commit()

    def list_claims(self, report_id: str) -> list[ClaimRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM claim_records WHERE report_id = ? ORDER BY created_at ASC",
                (report_id,),
            ).fetchall()
            return [ClaimRecord.from_mapping(dict(row)) for row in rows]

    def save_citation(self, citation: CitationRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO citation_records(
                    citation_id, claim_id, report_id, source, snippet,
                    document_id, page_number, chunk_id, evidence_id,
                    metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(citation_id) DO UPDATE SET
                    claim_id = excluded.claim_id,
                    report_id = excluded.report_id,
                    source = excluded.source,
                    snippet = excluded.snippet,
                    document_id = excluded.document_id,
                    page_number = excluded.page_number,
                    chunk_id = excluded.chunk_id,
                    evidence_id = excluded.evidence_id,
                    metadata = excluded.metadata
                """,
                (
                    citation.citation_id,
                    citation.claim_id,
                    citation.report_id,
                    citation.source,
                    citation.snippet,
                    citation.document_id,
                    citation.page_number,
                    citation.chunk_id,
                    citation.evidence_id,
                    json.dumps(citation.metadata, ensure_ascii=False),
                    citation.created_at,
                ),
            )
            conn.commit()

    def list_citations(
        self,
        *,
        report_id: str | None = None,
        claim_id: str | None = None,
    ) -> list[CitationRecord]:
        where: list[str] = []
        params: list[object] = []
        if report_id:
            where.append("report_id = ?")
            params.append(report_id)
        if claim_id:
            where.append("claim_id = ?")
            params.append(claim_id)
        sql = "SELECT * FROM citation_records"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [CitationRecord.from_mapping(dict(row)) for row in rows]

    def save_relation(self, relation: ClaimEvidenceRelation) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO claim_evidence_relations(
                    relation_id, claim_id, evidence_id, support_status,
                    confidence, method, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(relation_id) DO UPDATE SET
                    claim_id = excluded.claim_id,
                    evidence_id = excluded.evidence_id,
                    support_status = excluded.support_status,
                    confidence = excluded.confidence,
                    method = excluded.method,
                    metadata = excluded.metadata
                """,
                (
                    relation.relation_id,
                    relation.claim_id,
                    relation.evidence_id,
                    relation.support_status,
                    relation.confidence,
                    relation.method,
                    json.dumps(relation.metadata, ensure_ascii=False),
                    relation.created_at,
                ),
            )
            conn.commit()

    def list_relations_for_claim(self, claim_id: str) -> list[ClaimEvidenceRelation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM claim_evidence_relations
                WHERE claim_id = ?
                ORDER BY created_at ASC
                """,
                (claim_id,),
            ).fetchall()
            return [ClaimEvidenceRelation.from_mapping(dict(row)) for row in rows]

    def list_relations_for_evidence(self, evidence_id: str) -> list[ClaimEvidenceRelation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM claim_evidence_relations
                WHERE evidence_id = ?
                ORDER BY created_at ASC
                """,
                (evidence_id,),
            ).fetchall()
            return [ClaimEvidenceRelation.from_mapping(dict(row)) for row in rows]
