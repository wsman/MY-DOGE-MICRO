"""CLI command: macro — delegates to legacy macro.cli package.

The real macro report implementation lives in ``src/macro/cli.py`` and will be
migrated onto ``GenerateMacroReportUseCase`` in Sprint 007-006. Until then,
``doge macro`` simply forwards to the legacy entrypoint so behavior is preserved
and no report-generation capability is lost.
"""

import sys


def cmd_macro(args) -> None:
    """Forward ``doge macro`` to the legacy ``macro.cli`` package."""
    import macro.cli as legacy_macro_cli

    # Reconstruct the legacy argv so argparse sees the same flags.
    argv = ["macro.cli"]
    if getattr(args, "verbose", False):
        argv.append("--verbose")
    if getattr(args, "config_file", None):
        argv.extend(["--config-file", args.config_file])

    legacy_macro_cli.sys.argv = argv
    try:
        legacy_macro_cli.main()
    except SystemExit as exc:
        # Propagate the legacy exit code instead of overriding it.
        sys.exit(exc.code)
    # main() normally exits; if it returns, treat as success.
    sys.exit(0)
