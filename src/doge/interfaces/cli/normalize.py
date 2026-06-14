"""Shared CLI ticker normalization."""

import re


def normalize_ticker(ticker: str, market: str = "cn") -> str:
    """Normalize a bare CN code to its exchange-suffixed ticker.

    CN: ``6xx``/``68x`` -> ``.SH``, ``0xx``/``3xx`` -> ``.SZ``,
    ``4xx``/``8xx`` -> ``.BJ``. Non-CN markets and codes already containing a
    suffix are returned unchanged.

    Raises ``ValueError`` on malformed input.
    """
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    code = ticker.strip()
    if not code:
        raise ValueError("ticker cannot be empty")
    if len(code) > 20:
        raise ValueError("ticker too long (max 20 chars)")
    if not re.match(r"^[A-Za-z0-9.\\-]+$", code):
        raise ValueError("ticker contains invalid characters")

    if market != "cn" or "." in code:
        return code
    if code[0] == "6":
        return f"{code}.SH"
    elif code[0] in ("0", "3"):
        return f"{code}.SZ"
    elif code[0] in ("4", "8"):
        return f"{code}.BJ"
    return code
