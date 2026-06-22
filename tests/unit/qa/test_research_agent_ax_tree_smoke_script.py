import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "research_agent_ax_tree_smoke.py"


def test_research_agent_ax_tree_smoke_help_lists_runtime_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "--chrome-path" in result.stdout
    assert "--node-path" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--timeout-seconds" in result.stdout
