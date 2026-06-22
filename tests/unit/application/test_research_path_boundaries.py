from pathlib import Path

from doge.application.use_cases import generate_industry_report, generate_macro_report
from doge.application.use_cases import industry_analyzer, macro_strategist


def test_research_use_cases_declare_compatibility_vs_runtime_paths():
    assert generate_macro_report.RESEARCH_PATH == "compatibility_text_llm_report"
    assert generate_industry_report.RESEARCH_PATH == "compatibility_report_tool"
    assert macro_strategist.RESEARCH_PATH == "runtime_research_copilot"
    assert industry_analyzer.RESEARCH_PATH == "runtime_research_copilot"


def test_research_call_graph_documents_surface_ownership():
    text = Path("docs/progress/research-use-case-call-graph.md").read_text(encoding="utf-8")

    assert "Web `/research-agent` | Runtime Research Copilot" in text
    assert "Daemon `/v1/*` | Runtime Research Copilot" in text
    assert "API `/api/macro/run` | Compatibility report path" in text
    assert "CLI `macro` | Compatibility report path" in text
    assert "Tool `generate_industry_report` | Compatibility report tool" in text
    assert "Do not add another agent execution loop" in text
