"""Application package root.

Factory exports have been removed; use the bootstrap containers
(``doge.bootstrap.runtime.RuntimeContainer``,
``doge.bootstrap.gateway.GatewayContainer``,
``doge.bootstrap.workspace.WorkspaceContainer``) directly.
"""

from __future__ import annotations

from doge.application import contracts, use_cases

__all__ = ["contracts", "use_cases"]
