"""ADR lifecycle status contract tests for S002-011.

Governance gate: enforces the ADR lifecycle defined in ``docs/CLAUDE.md``::

    Status lifecycle: Proposed -> Accepted -> Superseded
    - Never skip Accepted — stories referencing a Proposed ADR are auto-blocked
    - ADR Dependencies must be Accepted before a dependent ADR is promoted

This test reads the Markdown of every ``docs/architecture/adr-*.md`` file and
asserts:

1. Each promoted ADR (ADR-0001/0002/0003/0004/0005/0009/0010) carries
   ``Status: Accepted``.
2. Each gated ADR (ADR-0007) carries ``Status: Proposed`` AND a
   ``Promotion gate`` callout in the Status section that names what is MET and
   what REMAINS.
3. No ADR has skipped ``Accepted`` — the only legal Status tokens are
   ``Proposed``, ``Accepted``, and ``Superseded``.
4. Each ``Promotion gate`` callout references the relevant story IDs and
   remaining work named in S002-011.

The test is deterministic and filesystem-only: it parses the ADR Markdown under
``docs/architecture/`` and asserts on the parsed Status section. No network,
no database, no external state.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Test constants — the ADR IDs and gate expectations are the load-bearing
# facts for this governance contract. Pinning them as module constants makes a
# lifecycle drift surface as a test failure, not a silent regression.
# --------------------------------------------------------------------------- #

_ARCH_DIR = Path(__file__).resolve().parents[3] / "docs" / "architecture"

# Legal Status tokens per docs/CLAUDE.md lifecycle.
_LEGAL_STATUSES = {"Proposed", "Accepted", "Superseded"}

# ADRs that S002-011 promotes to Accepted (gate met).
_EXPECTED_ACCEPTED = {
    "adr-0001": "ADR-0001 (brownfield-clean-architecture) — foundational; no promotion gates.",
    "adr-0002": "ADR-0002 (centralized-configuration) — gate met: get_settings singleton, frozen dataclasses, _env_path, reset_settings, tests/test_settings.py; ADR-0001 Accepted.",
    "adr-0003": "ADR-0003 (storage-repository-contract) — both gates met: S002-006 StorageWriteError + S002-007 DOGE_RETENTION_DAYS; IStockRepository/IReportRepository ports exist; SQLiteStorageRepository raises StorageWriteError.",
    "adr-0005": "ADR-0005 (llm-client-strategy) — gate met: OpenAI(api_key, base_url), stream=False temp=0.6, None-on-error, DEEPSEEK_API_KEY/DEEPSEEK_MODEL overrides; S002-013 closed the committed-key OPEN item.",
    "adr-0009": "ADR-0009 (cache-metadata-port-split) — Wave-4 accepted: ITickerNameCache + ITickerMetadataSource split realized; real yfinance metadata adapter is follow-on implementation work.",
    "adr-0010": "ADR-0010 (view-service-port-injection) — Wave-4 accepted: IMarketViewRepository + DuckDBMarketViewRepository + composition root are implemented and tested.",
    "adr-0004": "ADR-0004 (data-source-adapter-contract) — S004-004 promoted: TDXDataSource implements IMarketDataSource without NotImplementedError; tdx_downloader.py thin-wrapped as CLI shim; sys.path.insert removed (S002-005). _retry.py extraction deferred to a follow-on (not a promotion gate).",
}

# ADRs that STAY Proposed and must carry a Promotion gate callout.
# Each value maps the ADR stem -> a dict of (substr) -> required-mention substrings
# that must appear inside the Status section's Promotion-gate callout.
_EXPECTED_PROPOSED_GATES = {
    "adr-0007": {
        "met_keywords": ["S002-009", "error envelope"],
        "remains_keywords": [
            "allow_origins",                  # CORS hardening
            "CORS hardening",
            "loopback",
        ],
        "story_keywords": ["S002-009"],
    },
}

# ADR stems that exist but are NOT in either promotion set this sprint.
# Their Status is asserted legal (one of _LEGAL_STATUSES) but not pinned.
_OTHER_ADR_STEMS = {"adr-0006", "adr-0008"}


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

_STATUS_HEADING_RE = re.compile(r"^##\s+Status\s*$", re.MULTILINE)


def _extract_status_section(text: str) -> str:
    """Return the body of the ``## Status`` section up to the next ``## `` heading.

    The Status section is the authoritative lifecycle token per the ADR
    template. Parsing only this section keeps the contract robust against
    unrelated edits elsewhere in the document.
    """
    start_match = _STATUS_HEADING_RE.search(text)
    assert start_match is not None, "ADR has no '## Status' section"
    body_start = start_match.end()
    next_heading = re.search(r"^##\s+\S", text[body_start:], re.MULTILINE)
    if next_heading is None:
        return text[body_start:]
    return text[body_start : body_start + next_heading.start()]


def _parse_status_token(status_section: str) -> str:
    """Return the Status token (leading legal word) in the section.

    Tolerant of trailing parenthetical prose on the same line, e.g.
    ``Accepted (brownfield — reverse-documented 2026-06-12; ...)``
    which some brownfield ADRs carry. The Status token is always the first
    whitespace-delimited word of the first non-callout, non-blank content line
    in the section, and must be one of the legal lifecycle tokens.
    """
    for line in status_section.splitlines():
        stripped = line.strip()
        # Skip blank lines, blockquote callouts, and emphasis.
        if not stripped or stripped.startswith(">") or stripped.startswith("#"):
            continue
        # The Status token is the leading word; the rest of the line may be
        # an explanatory parenthetical (brownfield ADRs do this).
        first_word = stripped.split(None, 1)[0]
        if first_word in _LEGAL_STATUSES:
            return first_word
    pytest.fail(
        "Status section has no legal Status token "
        f"(one of {sorted(_LEGAL_STATUSES)}). Section was:\n{status_section}"
    )


def _load_adr(stem: str) -> tuple[str, str]:
    """Return (full_text, status_section) for the given ADR stem."""
    matches = sorted(_ARCH_DIR.glob(f"{stem}-*.md"))
    assert matches, f"No ADR file found for stem {stem!r} under {_ARCH_DIR}"
    assert len(matches) == 1, f"Multiple ADR files for stem {stem!r}: {matches}"
    text = matches[0].read_text(encoding="utf-8")
    return text, _extract_status_section(text)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestAdrLifecycleStatus:
    """Enforce the S002-011 ADR promotion/keep-Proposed decisions."""

    def test_accepted_adrs_are_accepted(self) -> None:
        # Arrange + Act + Assert — each promoted ADR must read Accepted.
        for stem in _EXPECTED_ACCEPTED:
            _, status_section = _load_adr(stem)
            token = _parse_status_token(status_section)
            assert token == "Accepted", (
                f"{stem} expected Accepted but is {token!r}. "
                f"Gate rationale: {_EXPECTED_ACCEPTED[stem]}"
            )

    @pytest.mark.parametrize("stem", sorted(_EXPECTED_PROPOSED_GATES))
    def test_gated_adrs_stay_proposed(self, stem: str) -> None:
        # Arrange
        gate = _EXPECTED_PROPOSED_GATES[stem]
        # Act
        _, status_section = _load_adr(stem)
        token = _parse_status_token(status_section)
        # Assert — must remain Proposed (gates not fully met this sprint, or
        # self-promotion intentionally deferred to Wave-4).
        assert token == "Proposed", (
            f"{stem} expected Proposed but is {token!r}. "
            "If its gate is now fully met, update this contract AND the "
            "S002-011 promotion table together."
        )

    @pytest.mark.parametrize("stem", sorted(_EXPECTED_PROPOSED_GATES))
    def test_gated_adrs_carry_promotion_gate_callout(self, stem: str) -> None:
        # Arrange
        gate = _EXPECTED_PROPOSED_GATES[stem]
        _, status_section = _load_adr(stem)
        callout = self._extract_callout(status_section, stem)
        # Assert — MET mentions.
        for kw in gate["met_keywords"]:
            assert kw in callout, (
                f"{stem} Promotion gate callout must mention MET keyword {kw!r}."
            )
        # Assert — REMAINS mentions.
        for kw in gate["remains_keywords"]:
            assert kw in callout, (
                f"{stem} Promotion gate callout must mention REMAINS keyword {kw!r}."
            )
        # Assert — story / review references.
        for kw in gate["story_keywords"]:
            assert kw in callout, (
                f"{stem} Promotion gate callout must reference {kw!r}."
            )

    def test_no_adr_skipped_accepted(self) -> None:
        """Every ADR's Status must be one of the three legal lifecycle tokens.

        This is the 'never skip Accepted' invariant: there is no legal Status
        that bypasses Accepted (e.g. no 'Implemented', 'Done', 'Active').
        """
        # Arrange
        all_adrs = sorted(_ARCH_DIR.glob("adr-*.md"))
        assert all_adrs, "No ADR files found under docs/architecture/"
        # Act + Assert
        for adr_path in all_adrs:
            text = adr_path.read_text(encoding="utf-8")
            status_section = _extract_status_section(text)
            token = _parse_status_token(status_section)
            assert token in _LEGAL_STATUSES, (
                f"{adr_path.name} has illegal Status {token!r}; "
                f"legal tokens are {sorted(_LEGAL_STATUSES)}."
            )

    def test_other_adrs_have_legal_status(self) -> None:
        """ADR-0006 / ADR-0008 are not in scope this sprint but must be legal."""
        # Arrange + Act + Assert
        for stem in _OTHER_ADR_STEMS:
            _, status_section = _load_adr(stem)
            token = _parse_status_token(status_section)
            assert token in _LEGAL_STATUSES, (
                f"{stem} has illegal Status {token!r}."
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_callout(status_section: str, stem: str) -> str:
        """Return the concatenated blockquote callout text under the Status token.

        ADRs kept Proposed carry a ``> **Promotion gate ...**`` blockquote
        immediately after the Status token. This joins all contiguous ``>``
        lines so keyword assertions span the whole callout.
        """
        lines = status_section.splitlines()
        callout_lines: list[str] = []
        seen_token = False
        in_callout = False
        for line in lines:
            stripped = line.strip()
            if not seen_token:
                # Tolerant match: the Status line may carry a parenthetical
                # (e.g. brownfield ADRs). Match on the leading word.
                first_word = stripped.split(None, 1)[0] if stripped else ""
                if first_word in _LEGAL_STATUSES:
                    seen_token = True
                continue
            # After the token, the callout is a contiguous run of '>' lines
            # (possibly separated by blank '>' lines).
            if stripped.startswith(">"):
                in_callout = True
                # Strip the leading '>' and surrounding whitespace for matching.
                callout_lines.append(stripped.lstrip(">").strip())
            elif stripped == "":
                # Blank line ends the callout run.
                if in_callout:
                    break
            else:
                # Non-callout, non-blank content ends the callout.
                if in_callout:
                    break
        assert callout_lines, (
            f"{stem} Status section has no Promotion gate callout (a contiguous "
            "blockquote after the Status token). S002-011 requires every kept-"
            "Proposed ADR to carry a 'Promotion gate' callout naming MET/REMAINS."
        )
        joined = " ".join(callout_lines)
        assert "Promotion gate" in joined, (
            f"{stem} callout must be introduced by 'Promotion gate'."
        )
        return joined
