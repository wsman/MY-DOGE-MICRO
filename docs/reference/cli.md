# CLI Reference Entry

The authoritative CLI contract remains [../CLI.md](../CLI.md).

This page gives the documentation index a stable lower-case reference path
without breaking tests and historical links that still target `docs/CLI.md`.

Important entrypoints:

- Console script: `doge`
- Main CLI source: `src/doge/interfaces/cli/main.py`
- Legacy compatibility shim: `src/cli.py`
- Macro compatibility path: `python -m macro.cli`
- Contract tests: `tests/cli/test_cli_arg_parsing.py`

Update [../CLI.md](../CLI.md) and the CLI tests together whenever command names,
flags, defaults, exit codes, or documented environment variables change.
