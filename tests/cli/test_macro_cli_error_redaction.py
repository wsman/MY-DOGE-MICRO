"""CLI error-path redaction test for S007-003.

When the legacy macro CLI catches an exception, it must not print the DeepSeek
API key or the placeholder sentinel to stdout/stderr. Covers the ``except``
block in ``src/macro/cli.py`` that prints the failure message.

Note: ``doge macro`` currently delegates to ``macro.cli.main()`` and therefore
inherits the same redaction behavior. When S007-06 migrates macro to the
application use case, this test should be retargeted at
``doge.interfaces.cli.commands.macro``.
"""
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

import macro.cli as macro_cli  # noqa: E402

FAKE_KEY = "sk-fake-test-key-not-real-1234567890"
PLACEHOLDER = "REPLACE_WITH_DEEPSEEK_API_KEY"


class TestCliErrorPathRedactsApiKey:
    def test_except_block_does_not_print_fake_key(self):
        with patch.object(macro_cli, "MacroConfig", side_effect=RuntimeError(
            f"auth failed for key={FAKE_KEY}"
        )), patch.object(macro_cli.sys, "exit") as mock_exit, \
           patch.object(macro_cli.sys, "argv", ["macro.cli"]), \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cli.main()

        output = captured.getvalue()
        assert FAKE_KEY not in output, (
            f"API key leaked into CLI stdout: {output!r}"
        )
        assert "<redacted>" in output
        mock_exit.assert_called_once_with(1)

    def test_except_block_does_not_print_placeholder(self):
        with patch.object(macro_cli, "MacroConfig", side_effect=RuntimeError(
            f"config still carries {PLACEHOLDER}"
        )), patch.object(macro_cli.sys, "exit") as mock_exit, \
           patch.object(macro_cli.sys, "argv", ["macro.cli"]), \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cli.main()

        output = captured.getvalue()
        assert PLACEHOLDER not in output, (
            f"Placeholder leaked into CLI stdout: {output!r}"
        )
        assert "<redacted>" in output
        mock_exit.assert_called_once_with(1)

    def test_except_block_redacts_when_config_is_unbound(self):
        with patch.object(macro_cli, "setup_logging", side_effect=RuntimeError(
            f"init failed with key={FAKE_KEY}"
        )), patch.object(macro_cli.sys, "exit") as mock_exit, \
           patch.object(macro_cli.sys, "argv", ["macro.cli"]), \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cli.main()

        output = captured.getvalue()
        assert FAKE_KEY not in output, (
            f"API key leaked into CLI stdout when config unbound: {output!r}"
        )
        mock_exit.assert_called_once_with(1)
