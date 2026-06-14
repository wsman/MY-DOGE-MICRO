"""Layer gate: no code under src/doge imports the legacy ai_analysis package.

S007-004 migrates ``src/ai_analysis`` helpers onto canonical ports and use
cases. This gate ensures the new canonical surface does not depend on the
legacy shim, preventing circular/dead dependencies once ``src/ai_analysis`` is
deleted in Sprint 008.
"""
import inspect
from pathlib import Path


class TestNoAiAnalysisUnderDoge:
    def test_doge_modules_do_not_import_ai_analysis(self):
        """No module under doge.* imports ai_analysis."""
        import doge

        pkg_path = Path(inspect.getfile(doge)).parent
        forbidden = ["from ai_analysis", "import ai_analysis"]
        hits = []
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    hits.append(
                        f"{source_path.relative_to(pkg_path)}: {pattern}"
                    )
        assert not hits, "legacy ai_analysis imports found under src/doge:\n" + "\n".join(hits)
