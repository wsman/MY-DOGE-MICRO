"""Adapter package marker for ADR-0022.

Concrete adapters remain in `doge.infrastructure` during the facade-first
migration. Re-export adapters here only when a story adds compatibility tests
for that adapter.
"""

__all__: list[str] = []
