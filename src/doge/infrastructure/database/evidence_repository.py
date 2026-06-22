"""SQLite repository for document pages, chunks, and evidence."""

from __future__ import annotations

import json
from pathlib import Path

from doge.config import get_settings
from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteEvidenceRepository(IEvidenceRepository):
    """Persist extracted document evidence in the agent SQLite database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def save_page(self, page: DocumentPage, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            effective_tenant_id = tenant_id if tenant_id is not None else _tenant_id_for_document(conn, page.document_id)
            conn.execute(
                """
                INSERT INTO document_pages(
                    page_id, tenant_id, document_id, page_number, text, image_metadata,
                    source_hash, parser_error, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, page_number) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    page_id = excluded.page_id,
                    text = excluded.text,
                    image_metadata = excluded.image_metadata,
                    source_hash = excluded.source_hash,
                    parser_error = excluded.parser_error
                """,
                (
                    page.page_id,
                    effective_tenant_id,
                    page.document_id,
                    page.page_number,
                    page.text,
                    json.dumps(page.image_metadata, ensure_ascii=False),
                    page.source_hash,
                    page.parser_error,
                    page.created_at,
                ),
            )
            conn.commit()

    def list_pages(self, document_id: str, tenant_id: str | None = None) -> list[DocumentPage]:
        sql = "SELECT * FROM document_pages WHERE document_id = ?"
        params: tuple[object, ...] = (document_id,)
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params = (document_id, tenant_id)
        sql += " ORDER BY page_number ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [DocumentPage.from_mapping(dict(row)) for row in rows]

    def save_chunk(self, chunk: DocumentChunk, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            effective_tenant_id = tenant_id if tenant_id is not None else _tenant_id_for_document(conn, chunk.document_id)
            conn.execute(
                """
                INSERT INTO document_chunks(
                    chunk_id, tenant_id, document_id, page_id, page_number, text,
                    start_char, end_char, source_hash, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    document_id = excluded.document_id,
                    page_id = excluded.page_id,
                    page_number = excluded.page_number,
                    text = excluded.text,
                    start_char = excluded.start_char,
                    end_char = excluded.end_char,
                    source_hash = excluded.source_hash
                """,
                (
                    chunk.chunk_id,
                    effective_tenant_id,
                    chunk.document_id,
                    chunk.page_id,
                    chunk.page_number,
                    chunk.text,
                    chunk.start_char,
                    chunk.end_char,
                    chunk.source_hash,
                    chunk.created_at,
                ),
            )
            conn.commit()

    def list_chunks(
        self,
        document_ids: list[str] | None = None,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[DocumentChunk]:
        if document_ids == []:
            return []
        sql = "SELECT * FROM document_chunks"
        params: list[object] = []
        where: list[str] = []
        if document_ids:
            placeholders = ", ".join("?" for _ in document_ids)
            where.append(f"document_id IN ({placeholders})")
            params.extend(document_ids)
        if tenant_id is not None:
            where.append("tenant_id = ?")
            params.append(tenant_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY document_id ASC, page_number ASC, start_char ASC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [DocumentChunk.from_mapping(dict(row)) for row in rows]

    def save_evidence(self, evidence: EvidenceRecord, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            effective_tenant_id = (
                tenant_id
                if tenant_id is not None
                else _tenant_id_for_run(conn, evidence.run_id) or _tenant_id_for_document(conn, evidence.document_id)
            )
            conn.execute(
                """
                INSERT INTO evidence_records(
                    evidence_id, tenant_id, run_id, document_id, page_id, chunk_id,
                    page_number, claim, support_snippet, relevance_score,
                    metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    run_id = excluded.run_id,
                    document_id = excluded.document_id,
                    page_id = excluded.page_id,
                    chunk_id = excluded.chunk_id,
                    page_number = excluded.page_number,
                    claim = excluded.claim,
                    support_snippet = excluded.support_snippet,
                    relevance_score = excluded.relevance_score,
                    metadata = excluded.metadata
                """,
                (
                    evidence.evidence_id,
                    effective_tenant_id,
                    evidence.run_id,
                    evidence.document_id,
                    evidence.page_id,
                    evidence.chunk_id,
                    evidence.page_number,
                    evidence.claim,
                    evidence.support_snippet,
                    evidence.relevance_score,
                    json.dumps(evidence.metadata, ensure_ascii=False),
                    evidence.created_at,
                ),
            )
            conn.commit()

    def get_evidence(self, evidence_id: str, tenant_id: str | None = None) -> EvidenceRecord | None:
        sql = "SELECT * FROM evidence_records WHERE evidence_id = ?"
        params: tuple[object, ...] = (evidence_id,)
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params = (evidence_id, tenant_id)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return EvidenceRecord.from_mapping(dict(row)) if row else None

    def list_evidence(
        self,
        *,
        run_id: str | None = None,
        document_id: str | None = None,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[EvidenceRecord]:
        where: list[str] = []
        params: list[object] = []
        if run_id:
            where.append("run_id = ?")
            params.append(run_id)
        if document_id:
            where.append("document_id = ?")
            params.append(document_id)
        if tenant_id is not None:
            where.append("tenant_id = ?")
            params.append(tenant_id)
        sql = "SELECT * FROM evidence_records"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [EvidenceRecord.from_mapping(dict(row)) for row in rows]


def _tenant_id_for_document(conn, document_id: str) -> str | None:
    row = conn.execute("SELECT tenant_id FROM documents WHERE document_id = ?", (document_id,)).fetchone()
    return row["tenant_id"] if row and row["tenant_id"] else None


def _tenant_id_for_run(conn, run_id: str | None) -> str | None:
    if not run_id:
        return None
    row = conn.execute("SELECT tenant_id FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row["tenant_id"] if row and row["tenant_id"] else None
