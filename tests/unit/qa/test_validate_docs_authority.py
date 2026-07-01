from pathlib import Path

from scripts.validate_docs_authority import validate


def test_docs_authority_accepts_current_repo_baseline():
    assert validate() == []


def test_docs_authority_rejects_new_bounded_context_copy(tmp_path: Path):
    _write(tmp_path / "docs/architecture/overview.md", "# Architecture Overview\n")
    _write(tmp_path / "docs/new-copy.md", "\n".join([
        "# Copy",
        "Market Intelligence",
        "Research",
        "Portfolio & Risk",
        "Quant & Data Lab",
        "Workspace & Workflow",
        "Agent Runtime",
        "Knowledge & Evidence",
        "Governance & Evaluation",
    ]))

    findings = validate(tmp_path)

    assert any(finding.fact == "bounded_contexts" for finding in findings)


def test_docs_authority_allows_pointer_without_restatement(tmp_path: Path):
    _write(tmp_path / "docs/architecture/overview.md", "# Architecture Overview\n")
    _write(
        tmp_path / "docs/start-here/architecture-reviewer.md",
        "Read [overview.md](../architecture/overview.md) for bounded contexts.\n",
    )

    assert validate(tmp_path) == []


def test_docs_authority_allows_adr_decision_history(tmp_path: Path):
    _write(tmp_path / "docs/architecture/overview.md", "# Architecture Overview\n")
    _write(tmp_path / "docs/architecture/adr-9999-example.md", "\n".join([
        "# ADR",
        "Market Intelligence",
        "Research",
        "Portfolio & Risk",
        "Quant & Data Lab",
        "Workspace & Workflow",
        "Agent Runtime",
        "Knowledge & Evidence",
        "Governance & Evaluation",
    ]))

    assert validate(tmp_path) == []


def test_docs_authority_rejects_runtime_path_copy(tmp_path: Path):
    _write(tmp_path / "docs/architecture/runtime-contracts.md", "# Runtime Contracts\n")
    _write(
        tmp_path / "docs/guides/runtime-copy.md",
        "process roots -> persisted runtime -> /v1 routes -> SDK clients\n",
    )

    findings = validate(tmp_path)

    assert any(finding.fact == "runtime_path" for finding in findings)


def test_docs_authority_rejects_shim_rule_copy(tmp_path: Path):
    _write(tmp_path / "docs/architecture/file-structure-policy.md", "# File Structure Policy\n")
    _write(
        tmp_path / "docs/guides/shim-copy.md",
        "Shim files may re-export, delegate, warn, and may not add routing logic.\n",
    )

    findings = validate(tmp_path)

    assert any(finding.fact == "shim_rules" for finding in findings)


def test_docs_authority_rejects_http_route_table_in_reference_shortcut(tmp_path: Path):
    _write(tmp_path / "docs/API.md", "# API\n")
    _write(
        tmp_path / "docs/reference/api.md",
        "\n".join(
            [
                "# HTTP API",
                "| Method | Path | Purpose |",
                "|---|---|---|",
                "| GET | /v1/sessions | list |",
                "| POST | /v1/sessions | create |",
                "| GET | /v1/runs/{run_id}/events | stream |",
            ]
        ),
    )

    findings = validate(tmp_path)

    assert any(finding.fact == "reference_http_table" for finding in findings)


def test_docs_authority_rejects_cli_command_table_in_reference_shortcut(tmp_path: Path):
    _write(tmp_path / "docs/CLI.md", "# CLI\n")
    _write(
        tmp_path / "docs/reference/cli.md",
        "\n".join(
            [
                "# CLI",
                "| Command | Purpose |",
                "|---|---|",
                "| `doge session` | local session |",
                "| `doge run` | batch run |",
                "| `doged serve` | daemon |",
            ]
        ),
    )

    findings = validate(tmp_path)

    assert any(finding.fact == "reference_cli_table" for finding in findings)


def test_docs_authority_rejects_mcp_tool_table_in_reference_shortcut(tmp_path: Path):
    _write(tmp_path / "docs/MCP_SERVER.md", "# MCP\n")
    _write(
        tmp_path / "docs/reference/tools.md",
        "\n".join(
            [
                "# Tools",
                "| Tool | Purpose |",
                "|---|---|",
                "| `market_scan` | scan market |",
                "| `portfolio_risk` | assess risk |",
                "| `memo_writer` | draft memo |",
            ]
        ),
    )

    findings = validate(tmp_path)

    assert any(finding.fact == "reference_tool_table" for finding in findings)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
