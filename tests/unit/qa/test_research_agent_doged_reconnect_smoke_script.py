from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "research_agent_doged_reconnect_smoke.py"


def test_research_agent_doged_reconnect_smoke_help_lists_runtime_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--output-dir" in result.stdout
    assert "--doged-port" in result.stdout
    assert "--timeout-seconds" in result.stdout


def test_research_agent_doged_reconnect_smoke_keeps_manual_boundary_explicit():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "research-agent-doged-reconnect-2026-06-22.json" in source
    assert "forced Research Agent SSE reconnect smoke disconnect" in source
    assert "ScriptedAgentModel" in source
    assert "not a manual screen-reader or operator-interruption pass" in source
