"""Deprecated CLI entrypoint — re-exported from ``doge.interfaces.cli``.

This file is kept as a backwards-compatible shim for Sprint 007. The canonical
CLI entrypoint is now ``doge.interfaces.cli.main`` and is exposed as the
``doge`` console script via ``[project.scripts]`` in ``pyproject.toml``.

This shim will be removed in Sprint 008.
"""

import warnings

warnings.warn(
    "src/cli.py is deprecated; use `python -m doge.interfaces.cli` or the "
    "installed `doge` command instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.cli.main import main

if __name__ == "__main__":
    main()
