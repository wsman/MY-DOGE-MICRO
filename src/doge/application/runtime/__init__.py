"""Canonical runtime application package.

Runtime implementation files remain under ``doge.application.agent`` while the
compatibility migration is active. New imports should target this package.
"""

from doge.application.runtime.kernel import RuntimeKernel

__all__ = ["RuntimeKernel"]
