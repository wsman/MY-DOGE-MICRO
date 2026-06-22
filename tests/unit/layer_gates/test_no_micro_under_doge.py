"""Layer gate: src/doge must not gain NEW legacy micro imports (S007-005).

S007-005 migrates local-file scanning from ``src/micro`` into canonical
doge.infrastructure adapters. A few existing adapters/routers still legitimately
import ``micro.*`` because their full migration is deferred to S007-008. This
gate blocks any *new* micro imports under ``src/doge`` while allowing the small,
documented allowlist of existing offenders.
"""
import inspect
from pathlib import Path


class TestNoNewMicroImportsUnderDoge:
    """Ensure no new legacy micro imports appear under src/doge."""

    # Existing files that legitimately import micro.* because their full
    # migration is deferred. Each entry must carry a reason and a story owner.
    ALLOWLIST = {
        # S007-005 deferred: SQLite single-logical-writer bridge; the legacy
        # save_stock_data_custom/init_db_custom helpers will be inlined or
        # replaced once the storage write path is fully canonicalized.
        "infrastructure/database/sqlite_storage.py": "legacy SQLite writer bridge (S007-008)",
    }

    FORBIDDEN = [
        "from micro",
        "import micro",
        "from src.micro",
        "import src.micro",
    ]

    def test_no_new_micro_imports_under_doge(self):
        """Only the documented allowlist may contain micro imports."""
        import doge

        pkg_path = Path(inspect.getfile(doge)).parent
        hits = []
        for source_path in pkg_path.rglob("*.py"):
            if source_path.name == "__init__.py":
                continue
            rel = source_path.relative_to(pkg_path).as_posix()
            text = source_path.read_text(encoding="utf-8")
            has_forbidden = any(pattern in text for pattern in self.FORBIDDEN)
            if not has_forbidden:
                continue
            if rel in self.ALLOWLIST:
                continue
            for pattern in self.FORBIDDEN:
                if pattern in text:
                    hits.append(f"{rel}: {pattern}")
                    break

        assert not hits, (
            "new legacy micro imports found under src/doge:\n"
            + "\n".join(hits)
            + "\n\nIf this is an existing deferred migration, add it to ALLOWLIST "
            "with a story owner; otherwise remove the import."
        )

    def test_allowlist_is_documented_and_small(self):
        """The allowlist must not grow silently."""
        assert len(self.ALLOWLIST) <= 6, (
            "ALLOWLIST has grown; review deferred migrations before adding more."
        )
