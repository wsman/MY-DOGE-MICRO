"""CLI command: macro."""

import sys

from doge.application.contracts.request import GenerateMacroReportRequest
from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA, MACRO_API_KEY_HINT_EN, MACRO_FAIL_PREFIX


def cmd_macro(args) -> None:
    """Generate a compatibility macro report through ``GenerateMacroReportUseCase``."""
    try:
        response = build_generate_macro_report_use_case().execute(
            GenerateMacroReportRequest(market=getattr(args, "market", "cn"))
        )
    except Exception:
        print(f"{MACRO_FAIL_PREFIX} <redacted>")
        print(MACRO_API_KEY_HINT_EN)
        sys.exit(EXIT_NO_DATA)
        return

    if response.error:
        print(f"{MACRO_FAIL_PREFIX} {response.error}")
        print(MACRO_API_KEY_HINT_EN)
        sys.exit(EXIT_NO_DATA)
        return

    print(response.content)
    sys.exit(0)


def _gateway_container():
    return build_gateway_container()


def build_generate_macro_report_use_case():
    return _gateway_container().build_generate_macro_report_use_case()
