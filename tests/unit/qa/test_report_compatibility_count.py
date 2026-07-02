"""Tests for the compatibility-surface count trend reporter (K-4)."""

from pathlib import Path

import scripts.report_compatibility_count as reporter


def test_parses_all_registry_rows_without_failures():
    counts, failures = reporter.parse()

    assert failures == [], (
        "every registry surface must have a current_count starting with an "
        "integer: " + ", ".join(f.surface for f in failures)
    )
    assert len(counts) >= 3  # floor; Sprint M retired most surfaces (composition, agent.tools, v1, micro/macro/interface)


def test_report_never_sums_across_heterogeneous_units():
    counts, _ = reporter.parse()

    out = reporter.render(counts, [])

    assert "Per-unit subtotals (never summed across units)" in out
    # No single grand-total line crosses units.
    assert "grand total" not in out.lower()
    # Multiple distinct units exist (callables, python-file, etc.) and each has
    # its own subtotal row rather than one combined number.
    assert out.count("| unit | subtotal") >= 1


def test_check_mode_does_not_write_the_report_file(tmp_path: Path, monkeypatch):
    # Point the reporter at a tmp registry so the real repo is untouched.
    registry = tmp_path / "registry.md"
    registry.write_text(
        "## Surface Registry\n"
        "| surface | type | parity_tests | earliest_removal | current_count |\n"
        "|---|---|---|---|---|\n"
        "| `a` | legacy | tests | story | 6 Python files, verified |\n"
        "| `b` | shim | tests | story | 3 public callables, verified |\n",
        encoding="utf-8",
    )
    report_file = tmp_path / "compatibility-count.md"
    monkeypatch.setattr(reporter, "REGISTRY", registry)
    monkeypatch.setattr(reporter, "REPORT", report_file)

    rc = reporter.main(["--check"])

    assert rc == 0
    assert not report_file.exists(), "--check must not write the report file"


def test_write_mode_appends_a_timestamped_section(tmp_path: Path, monkeypatch):
    registry = tmp_path / "registry.md"
    registry.write_text(
        "## Surface Registry\n"
        "| surface | current_count |\n"
        "|---|---|\n"
        "| `a` | 6 Python files, verified |\n",
        encoding="utf-8",
    )
    report_file = tmp_path / "compatibility-count.md"
    monkeypatch.setattr(reporter, "REGISTRY", registry)
    monkeypatch.setattr(reporter, "REPORT", report_file)

    rc = reporter.main(["--write"])

    assert rc == 0
    text = report_file.read_text(encoding="utf-8")
    assert "Compatibility Surface Count Trend" in text
    assert "| surface | count | unit |" in text
    assert "`a`" in text and "6" in text
