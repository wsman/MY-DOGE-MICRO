"""Public Agent Runtime bounded-context contract.

The runtime context owns sessions, runs, events, worker coordination, model
execution, tool execution, artifact finalization, approvals, and cancellation.
During the ADR-0022 compatibility window, this package re-exports current
implementation objects from `doge.application.agent` and runtime service
protocols from `doge.core.ports.runtime_services`.
"""
