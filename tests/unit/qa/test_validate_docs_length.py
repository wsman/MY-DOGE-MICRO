from pathlib import Path

import scripts.validate_docs_length as validator


def test_docs_length_accepts_current_docs():
    assert validator.validate() == []


def test_docs_length_rejects_short_start_here(tmp_path: Path, monkeypatch):
    start_here = tmp_path / "docs" / "start-here"
    start_here.mkdir(parents=True)
    (start_here / "short.md").write_text("# Short\n", encoding="utf-8")
    monkeypatch.setattr(validator, "START_HERE_DIR", start_here)
    monkeypatch.setattr(validator, "GUIDES_DIR", tmp_path / "docs" / "guides")
    monkeypatch.setattr(validator, "REDIRECT_STUBS", ())
    monkeypatch.setattr(validator, "SHORT_ENTRY_DOCS", ())

    findings = validator.validate()

    assert any("expected 80-120 lines" in finding.message for finding in findings)


def test_docs_length_rejects_long_guide(tmp_path: Path, monkeypatch):
    guides = tmp_path / "docs" / "guides"
    guides.mkdir(parents=True)
    (guides / "long.md").write_text("\n".join(["# Long"] * 401), encoding="utf-8")
    monkeypatch.setattr(validator, "START_HERE_DIR", tmp_path / "docs" / "start-here")
    monkeypatch.setattr(validator, "GUIDES_DIR", guides)
    monkeypatch.setattr(validator, "REDIRECT_STUBS", ())
    monkeypatch.setattr(validator, "SHORT_ENTRY_DOCS", ())

    findings = validator.validate()

    assert any("hard cap" in finding.message for finding in findings)


def test_docs_length_rejects_large_redirect_stub(tmp_path: Path, monkeypatch):
    stub = tmp_path / "docs" / "reference" / "api.md"
    stub.parent.mkdir(parents=True)
    stub.write_text("\n".join(["# Stub"] * 81), encoding="utf-8")
    monkeypatch.setattr(validator, "START_HERE_DIR", tmp_path / "docs" / "start-here")
    monkeypatch.setattr(validator, "GUIDES_DIR", tmp_path / "docs" / "guides")
    monkeypatch.setattr(validator, "REDIRECT_STUBS", (stub,))
    monkeypatch.setattr(validator, "SHORT_ENTRY_DOCS", ())

    findings = validator.validate()

    assert any("redirect entry exceeds" in finding.message for finding in findings)


def test_docs_length_rejects_large_short_entry_doc(tmp_path: Path, monkeypatch):
    entry = tmp_path / "docs" / "progress" / "current-status.md"
    entry.parent.mkdir(parents=True)
    entry.write_text("\n".join(["# Entry"] * 101), encoding="utf-8")
    monkeypatch.setattr(validator, "START_HERE_DIR", tmp_path / "docs" / "start-here")
    monkeypatch.setattr(validator, "GUIDES_DIR", tmp_path / "docs" / "guides")
    monkeypatch.setattr(validator, "REDIRECT_STUBS", ())
    monkeypatch.setattr(validator, "SHORT_ENTRY_DOCS", (entry,))

    findings = validator.validate()

    assert any("short entry doc exceeds" in finding.message for finding in findings)
