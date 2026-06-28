# RuntimeKernel Contract

`RuntimeKernel` is the persisted research-agent runtime facade. It accepts
legacy string arguments and scope-first calls, resolves arguments through
`doge.application.agent.runtime_args`, then delegates to collaborators defined by
`doge.core.ports.runtime_services`.

Invariant: Kernel delegates; collaborators decide.

## Public Operations

| Method | Collaborator | Return |
|---|---|---|
| `create_run` | `IRunLifecycleService.create_run` | `AgentRun` |
| `run_to_pause_or_completion` | `IRunLifecycleService.run_to_pause_or_completion` | `AgentRun` |
| `queue_run` | `IRunLifecycleService.queue_run` | `AgentRun` |
| `step` | `IRunStepper.step` | `AgentRun` |
| `resolve_approval` | `IApprovalCoordinator.resolve` | `AgentRun` |
| `cancel_run` | `IRunLifecycleService.cancel_run` | `AgentRun` |
| `finalize_cancelled` | `IRunLifecycleService.finalize_cancelled` | `AgentRun` |
| `record_failure` | `IRunLifecycleService.record_failure` | `AgentRun` |
| `get_run` | `IRunLifecycleService.get_run` | `AgentRun | None` |
| `list_events` | `IRunLifecycleService.list_events` | `list[AgentEvent]` |
| `list_runs` | `IRunLifecycleService.list_runs` | `list[AgentRun]` |
| `list_artifacts` | `IRunLifecycleService.list_artifacts` | `list[AgentArtifact]` |

## Collaborators

`IRunLifecycleService` owns run creation, execution loops, queueing, cancel
requests, failure recording, and read-model access.

`IRunStepper` owns one model/tool execution round.

`IApprovalCoordinator` owns approval resolution.

`ITransitionRecorder` owns transactional state recording.

`IArtifactFinalizer` owns artifact construction and artifact metrics.

## Boundary

`RuntimeKernel` must not contain state-machine rules, approval decisions, model
execution logic, tool execution logic, artifact metrics, backend routing,
session lifecycle rules, or direct repository persistence. Those decisions live
in the collaborators and platform services behind the core ports.
