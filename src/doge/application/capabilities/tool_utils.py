"""Compatibility re-export; canonical home is ``doge.shared.tool_utils``.

Kept so existing ``from doge.application.capabilities.tool_utils import ...``
imports keep resolving while consumers migrate to ``doge.shared.tool_utils``.
"""

from doge.shared.tool_utils import (  # noqa: F401
    ServiceFactory,
    claim_matches_evidence,
    claim_matches_rows,
    document_scope_from_context,
    filter_results_for_context,
    is_restricted_context,
    looks_mutating_sql,
    num,
    resolve,
    unsafe_python,
)
