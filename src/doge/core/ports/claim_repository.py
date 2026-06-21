"""Repository port for report claims and citations."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.claim_models import CitationRecord, ClaimRecord


class IClaimRepository(Protocol):
    """Persist and retrieve material report claims and their citations."""

    def save_claim(self, claim: ClaimRecord) -> None:
        ...

    def list_claims(self, report_id: str) -> list[ClaimRecord]:
        ...

    def save_citation(self, citation: CitationRecord) -> None:
        ...

    def list_citations(
        self,
        *,
        report_id: str | None = None,
        claim_id: str | None = None,
    ) -> list[CitationRecord]:
        ...
