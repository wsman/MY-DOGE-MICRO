"""Tests for CLI exit codes."""

import pytest

from doge.interfaces.cli import main
from doge.interfaces.cli.constants import EXIT_NO_DATA


class TestCliExitCodes:
    @pytest.mark.parametrize("argv", [
        ["stock", "AAPL", "--market", "hk"],
        ["rsrs", "--market", "jp"],
        ["breadth", "--market", "global"],
    ])
    def test_invalid_market_exits_2(self, argv):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 2

    def test_anomaly_rejects_market_flag_with_exit_2(self):
        with pytest.raises(SystemExit) as exc:
            main(["anomaly", "--market", "cn"])
        assert exc.value.code == 2

    def test_no_subcommand_prints_help_and_exits_0(self, capsys):
        # main([]) prints help and returns (does not raise).
        main([])
        assert "usage: doge" in capsys.readouterr().out

    def test_help_exits_0(self):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        # Output is on stderr for argparse --help.
