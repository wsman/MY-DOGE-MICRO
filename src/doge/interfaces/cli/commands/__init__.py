"""CLI command exports."""

from doge.interfaces.cli.commands.anomaly import cmd_anomaly
from doge.interfaces.cli.commands.breadth import cmd_breadth
from doge.interfaces.cli.commands.demo import cmd_demo
from doge.interfaces.cli.commands.macro import cmd_macro
from doge.interfaces.cli.commands.rsrs import cmd_rsrs
from doge.interfaces.cli.commands.stock import cmd_stock

__all__ = [
    "cmd_stock",
    "cmd_rsrs",
    "cmd_breadth",
    "cmd_anomaly",
    "cmd_demo",
    "cmd_macro",
]
