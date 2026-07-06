"""CLI command exports."""

from doge.interfaces.cli.commands.anomaly import cmd_anomaly
from doge.interfaces.cli.commands.batch import cmd_batch
from doge.interfaces.cli.commands.brief import cmd_brief
from doge.interfaces.cli.commands.breadth import cmd_breadth
from doge.interfaces.cli.commands.case import cmd_case
from doge.interfaces.cli.commands.demo import cmd_demo
from doge.interfaces.cli.commands.demo_pack import cmd_demo_pack
from doge.interfaces.cli.commands.doctor import cmd_doctor
from doge.interfaces.cli.commands.export import cmd_export
from doge.interfaces.cli.commands.macro import cmd_macro
from doge.interfaces.cli.commands.run import cmd_run
from doge.interfaces.cli.commands.rsrs import cmd_rsrs
from doge.interfaces.cli.commands.session import cmd_session
from doge.interfaces.cli.commands.slots import cmd_slots
from doge.interfaces.cli.commands.start import cmd_start
from doge.interfaces.cli.commands.stock import cmd_stock
from doge.interfaces.cli.commands.template import cmd_template

__all__ = [
    "cmd_stock",
    "cmd_rsrs",
    "cmd_breadth",
    "cmd_anomaly",
    "cmd_batch",
    "cmd_brief",
    "cmd_case",
    "cmd_demo",
    "cmd_demo_pack",
    "cmd_doctor",
    "cmd_export",
    "cmd_macro",
    "cmd_run",
    "cmd_session",
    "cmd_slots",
    "cmd_start",
    "cmd_template",
]
