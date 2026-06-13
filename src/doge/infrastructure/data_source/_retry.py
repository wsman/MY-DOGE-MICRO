"""Shared retry helper for MarketDataSource adapters and legacy loaders.

Extracted as ADR-0004 Migration Plan step 2 (``docs/architecture/
adr-0004-data-source-adapter-contract.md:219``). Prior to this module, three
near-identical retry loops existed:

* ``src/macro/data_loader.py`` — ``GlobalMacroLoader.fetch_combined_data``
  (3 retries, 5s fixed delay, 429 substring heuristic, ``None`` on exhaustion).
* ``src/doge/infrastructure/data_source/yfinance.py`` —
  ``YFinanceDataSource._fetch_with_retry`` (same defaults; canonical source
  of the ``_is_rate_limited`` predicate, docstring cites
  ``data_loader.py:94-97``).
* ``src/doge/infrastructure/data_source/tdx.py`` —
  ``TDXDataSource._fetch_with_retry`` (same defaults, ``None`` on exhaustion).

This helper consolidates them into a single behavior-preserving primitive.
The control flow mirrors the original loops EXACTLY so the existing retry
test batteries (``tests/test_yfinance_adapter.py``,
``tests/test_tdx_adapter.py``, ``tests/unit/macro/test_data_loader_rsrs.py``)
serve as the parity guard.

Contract
--------
* ``None`` on exhaustion (ADR-0004 item 2 — never raises for transient
  failure; callers treat ``None`` as the degraded signal).
* Non-retryable exceptions re-raise immediately (preserves the existing
  error surfacing for genuine programmer errors).
* Empty / ``None`` results are treated as retryable — they are usually the
  first symptom of an upstream rate-limit response that did not surface as
  an HTTP 429.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)

# A successful fetcher return value — yfinance returns a DataFrame, TDX returns
# a list[dict] of bars. ``None`` is reserved as the exhaustion sentinel.
FetchResult = Union[Any, None]


def is_rate_limited(error: BaseException) -> bool:
    """Return True when *error* looks like a Yahoo Finance rate-limit response.

    Reuses the canonical heuristic string match originally from
    ``src/macro/data_loader.py`` (lines 94-97) and the yfinance adapter's
    ``_is_rate_limited``: "Rate", "429", or "Too Many Requests" in the error
    message. This is intentionally permissive — it errs on the side of
    retrying so the ``None``-on-exhaustion degraded path is only reached
    after a real delay budget has been spent.
    """
    message = str(error)
    return any(token in message for token in ("Rate", "429", "Too Many Requests"))


def fetch_with_retry(
    fetcher: Callable[[], FetchResult],
    *,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    is_retryable: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[int, int, BaseException], None]] = None,
    label: str = "",
) -> FetchResult:
    """Call *fetcher* with bounded retry on transient / rate-limit errors.

    Args:
        fetcher: Zero-argument thunk that performs the actual fetch
            (e.g. ``lambda: yf.download(...)``). Returning ``None`` or an
            empty container (DataFrame, list) triggers a retry.
        max_retries: Maximum number of attempts. Defaults to ``3`` per
            ADR-0004 item 3.
        retry_delay: Fixed delay in seconds between attempts. Defaults to
            ``5.0`` per ADR-0004 item 3. No exponential backoff — preserving
            the legacy behavior is the parity contract.
        is_retryable: Predicate over the caught exception. Returns ``True``
            to continue the retry loop, ``False`` to re-raise immediately.
            Defaults to :func:`is_rate_limited`.
        on_retry: Optional ``(attempt, max_retries, exc)`` hook called before
            each retry sleep. Used by callers to emit their own structured
            log lines (keeps this helper free of caller-specific log
            formatting).
        label: Optional human-readable identifier included in this helper's
            own log lines (e.g. the ticker being fetched). Empty by default.

    Returns:
        The fetcher's non-empty result, or ``None`` if every attempt
        produced a retryable exception or empty result.

    Raises:
        Re-raises the original exception when ``is_retryable(exc)`` returns
        ``False`` (genuine programmer / non-transient errors).
    """
    predicate = is_retryable if is_retryable is not None else is_rate_limited
    last_error: Optional[BaseException] = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                if on_retry is not None and last_error is not None:
                    on_retry(attempt + 1, max_retries, last_error)
                time.sleep(retry_delay)

            data = fetcher()

            # Empty / None result is treated as retryable — empty responses
            # are usually the first symptom of an upstream rate limit that
            # never surfaced as an HTTP 429.
            if data is None:
                last_error = RuntimeError("empty response (possible rate limit)")
                if attempt > 0 and on_retry is not None:
                    on_retry(attempt + 1, max_retries, last_error)
                continue
            if hasattr(data, "empty") and bool(getattr(data, "empty", False)):
                last_error = RuntimeError("empty response (possible rate limit)")
                if attempt > 0 and on_retry is not None:
                    on_retry(attempt + 1, max_retries, last_error)
                continue
            if isinstance(data, (list, tuple)) and len(data) == 0:
                last_error = RuntimeError("empty response (possible rate limit)")
                if attempt > 0 and on_retry is not None:
                    on_retry(attempt + 1, max_retries, last_error)
                continue

            return data

        except Exception as err:  # noqa: BLE001 - adapters raise varied errors
            last_error = err
            if not predicate(err):
                # Non-retryable — surface immediately (preserves the legacy
                # behavior for genuine programmer errors).
                raise
            # Retryable; loop continues (sleep happens on the next iteration).

    logger.error(
        "%s exhausted %d retries: %s", label or "fetch_with_retry", max_retries, last_error
    )
    return None
