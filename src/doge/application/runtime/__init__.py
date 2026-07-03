"""DEPRECATED (ADR-0027): legacy runtime application facade.

Compatibility re-export retained for the ADR-0022/0027 migration window. The
canonical runtime facade is ``doge.platform.runtime``; new imports must target
it. Do not add behavior here. Scheduled for removal once no compatibility
consumer remains.
"""

from doge.application.runtime.kernel import RuntimeKernel

__all__ = ["RuntimeKernel"]
