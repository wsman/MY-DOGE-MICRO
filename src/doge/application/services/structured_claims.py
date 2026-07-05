"""Build product-facing structured claim records for research artifacts."""

from __future__ import annotations

import re
from typing import Any


def build_structured_claims(
    claims: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    relations: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return matrix-ready claim rows derived from existing claim/citation data."""
    relation_by_claim = _relations_by_claim(relations or [])
    citations_by_claim = _citations_by_claim(citations)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in claims:
        claim_text = _text(raw.get("claim_text") or raw.get("text") or raw.get("claim"))
        if not claim_text:
            continue
        claim_id = _text(raw.get("claim_id")) or f"claim-{len(rows) + 1}"
        if claim_id in seen:
            continue
        seen.add(claim_id)
        claim_relations = relation_by_claim.get(claim_id, [])
        evidence_refs = _evidence_refs_for_claim(citations_by_claim.get(claim_id, []), claim_relations)
        status = _claim_status(raw, claim_relations)
        numeric_check_status = _numeric_check_status(claim_text, evidence_refs)
        rows.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "status": status,
                "support_status": status,
                "evidence_refs": evidence_refs,
                "evidence_count": len(evidence_refs) or int(raw.get("evidence_count") or 0),
                "numeric_check_status": numeric_check_status,
                "risk_level": _risk_level(status, numeric_check_status, evidence_refs),
            }
        )
    return rows


def merge_structured_claim_fields(
    claims: list[dict[str, Any]],
    structured_claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add structured-claim fields to existing RunClaimResponse-shaped rows."""
    by_id = {str(item.get("claim_id")): item for item in structured_claims if item.get("claim_id")}
    by_text = {str(item.get("claim_text")): item for item in structured_claims if item.get("claim_text")}
    merged: list[dict[str, Any]] = []
    for claim in claims:
        structured = by_id.get(str(claim.get("claim_id"))) or by_text.get(str(claim.get("claim_text")))
        if not structured:
            merged.append(claim)
            continue
        updated = dict(claim)
        updated.update(
            {
                "status": structured.get("status", ""),
                "evidence_refs": structured.get("evidence_refs", []),
                "numeric_check_status": structured.get("numeric_check_status", "not_checked"),
                "risk_level": structured.get("risk_level", "medium"),
            }
        )
        if structured.get("evidence_count") is not None:
            updated["evidence_count"] = structured["evidence_count"]
        merged.append(updated)
    return merged


def _relations_by_claim(relations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for relation in relations:
        claim_id = _text(relation.get("claim_id"))
        if claim_id:
            grouped.setdefault(claim_id, []).append(relation)
    return grouped


def _citations_by_claim(citations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        claim_id = _text(citation.get("claim_id"))
        if claim_id:
            grouped.setdefault(claim_id, []).append(citation)
    return grouped


def _claim_status(raw: dict[str, Any], relations: list[dict[str, Any]]) -> str:
    for relation in relations:
        status = _normalize_status(_text(relation.get("support_status")))
        if status == "contradicted":
            return status
    raw_status = _normalize_status(_text(raw.get("status") or raw.get("support_status")))
    if raw_status != "unverified":
        return raw_status
    if any(_normalize_status(_text(item.get("support_status"))) == "supported" for item in relations):
        return "supported"
    if relations:
        return "partial"
    return "unverified"


def _normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"supported", "partial"}:
        return normalized
    if normalized in {"contradicted", "conflicted", "conflict", "contradiction"}:
        return "contradicted"
    if normalized in {"insufficient_evidence", "insufficient", "unsupported", "unrelated", "missing"}:
        return "insufficient_evidence"
    return "unverified"


def _evidence_ref(citation: dict[str, Any]) -> dict[str, Any]:
    evidence_id = _text(citation.get("evidence_id"))
    citation_id = _text(citation.get("citation_id"))
    source = _text(citation.get("source"))
    snippet = _text(citation.get("snippet") or citation.get("support_snippet"))
    ref = {
        "citation_id": citation_id,
        "evidence_id": evidence_id,
        "source": source,
        "document_id": citation.get("document_id"),
        "page_number": citation.get("page_number"),
        "chunk_id": citation.get("chunk_id"),
        "snippet": snippet,
    }
    return {key: value for key, value in ref.items() if value not in ("", None)}


def _evidence_refs_for_claim(
    citations: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refs = [_evidence_ref(item) for item in citations]
    refs = [item for item in refs if item]
    relation_evidence_ids = [_text(item.get("evidence_id")) for item in relations]
    relation_evidence_ids = [item for item in relation_evidence_ids if item]

    for index, ref in enumerate(refs):
        if ref.get("evidence_id") or index >= len(relation_evidence_ids):
            continue
        ref["evidence_id"] = relation_evidence_ids[index]

    seen = {_text(ref.get("evidence_id")) for ref in refs if ref.get("evidence_id")}
    for evidence_id in relation_evidence_ids:
        if evidence_id in seen:
            continue
        refs.append({"evidence_id": evidence_id})
        seen.add(evidence_id)
    return refs


def _numeric_check_status(claim_text: str, evidence_refs: list[dict[str, Any]]) -> str:
    claim_numbers = _numbers(claim_text)
    if not claim_numbers:
        return "not_applicable"
    evidence_numbers: list[float] = []
    for ref in evidence_refs:
        evidence_numbers.extend(_numbers(ref.get("snippet", "")))
    if not evidence_numbers:
        return "not_checked"
    matched = all(any(_near(value, other) for other in evidence_numbers) for value in claim_numbers)
    return "passed" if matched else "failed"


def _risk_level(status: str, numeric_check_status: str, evidence_refs: list[dict[str, Any]]) -> str:
    if status == "contradicted" or numeric_check_status == "failed":
        return "high"
    if status != "supported" or numeric_check_status == "not_checked" or not evidence_refs:
        return "medium"
    return "low"


def _numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    text = str(value)
    return [float(item) for item in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", text.replace("%", ""))]


def _near(left: float, right: float) -> bool:
    return abs(left - right) <= max(0.01, abs(right) * 0.01)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
