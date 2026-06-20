"""CLI error-path redaction tests for the canonical macro command."""

from io import StringIO
from unittest.mock import patch

from doge.interfaces.cli.commands import macro as macro_cmd

FAKE_KEY = "sk-fake-test-key-not-real-1234567890"
PLACEHOLDER = "REPLACE_WITH_DEEPSEEK_API_KEY"


class _Args:
    market = "cn"
    verbose = False
    config_file = None


class TestCliErrorPathRedactsApiKey:
    def test_except_block_does_not_print_fake_key(self):
        with patch.object(macro_cmd, "build_generate_macro_report_use_case", side_effect=RuntimeError(
            f"auth failed for key={FAKE_KEY}"
        )), patch.object(macro_cmd.sys, "exit") as mock_exit, \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cmd.cmd_macro(_Args())

        output = captured.getvalue()
        assert FAKE_KEY not in output, (
            f"API key leaked into CLI stdout: {output!r}"
        )
        assert "<redacted>" in output
        mock_exit.assert_called_once_with(1)

    def test_except_block_does_not_print_placeholder(self):
        with patch.object(macro_cmd, "build_generate_macro_report_use_case", side_effect=RuntimeError(
            f"config still carries {PLACEHOLDER}"
        )), patch.object(macro_cmd.sys, "exit") as mock_exit, \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cmd.cmd_macro(_Args())

        output = captured.getvalue()
        assert PLACEHOLDER not in output, (
            f"Placeholder leaked into CLI stdout: {output!r}"
        )
        assert "<redacted>" in output
        mock_exit.assert_called_once_with(1)

    def test_except_block_redacts_when_config_is_unbound(self):
        with patch.object(macro_cmd, "build_generate_macro_report_use_case", side_effect=RuntimeError(
            f"init failed with key={FAKE_KEY}"
        )), patch.object(macro_cmd.sys, "exit") as mock_exit, \
           patch("sys.stdout", new=StringIO()) as captured:
            macro_cmd.cmd_macro(_Args())

        output = captured.getvalue()
        assert FAKE_KEY not in output, (
            f"API key leaked into CLI stdout when config unbound: {output!r}"
        )
        mock_exit.assert_called_once_with(1)
