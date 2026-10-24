# Tasks

## 1. Native mise Boundary

- [x] 1.1 Keep mise's state with the disposable directory of every resolution and disposable provisioning; done when a real-mise regression proves that resolving declared version files, a locked tool and a locked environment leaves the host's mise state unchanged, runs no repository task and returns the locked executables (`test_native_supply_resolution_leaves_no_host_mise_state`; provisioning: `tests/unit/ci/test_hosted_tool_supply.py`).
- [x] 1.2 Give admitted commands the locked environment without resolution's safe mode or state, carrying the caller's explicit safe mode and state directory as given; done when real-mise regressions prove that an admitted task and its nested task run, that caller-selected safe mode still refuses tasks, and that untrusted code-running configuration never runs and gains no trust record (`test_locked_execution_runs_admitted_tasks_under_native_mise_policy`, `test_locked_execution_leaves_trust_to_native_mise`).

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
- After the successor runtime that carries the fix is active, remove the earlier records with `mise prune --configs`.
