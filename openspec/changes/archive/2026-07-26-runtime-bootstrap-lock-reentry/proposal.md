## Why

A full ETHOS proof runs its Python owner under an outer `uv` process. The armed
reference-transaction hook can then request the exact current worktree's
semantic Python with `ETHOS_RUNTIME_BOOTSTRAPPED=1` already in its environment.
The bootstrap still performs `uv sync --check` and can fall back to a nested
`uv run`, which waits on the outer process's runtime lock. The result is a real
proof deadlock with no valid proof receipt and no ref advance.

## What Changes

- Directly execute a healthy, exact current-worktree semantic Python request
  when the explicit bootstrap marker is already set, instead of re-entering
  `uv` synchronization.
- Preserve the existing fallback for an absent, invalid, unmarked, or
  non-semantic interpreter request.
- Add a focused regression that proves the marked semantic re-entry makes no
  nested `uv` invocation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=runtime-bootstrap-lock-reentry;
  reuse=extend; change=modify; facet:lifecycle=runtime,validation;
  facet:surface=hook,ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence. The worktree-bound
  runtime bootstrap safely handles marked semantic-Python re-entry during hook
  and proof execution without weakening runtime or ref admission.

## Impact

- `tools/ci/scripts/with-python-runtime.sh`
- `tests/unit/governance/test_generated_artifact_runtime.py`
- Repository-governance OpenSpec requirement, Claim, and Chronicle evidence

## Out Of Scope

- Reference-transaction policy, candidate routing, leases, or closeout
  authorization.
- General `ETHOS_RUNTIME_BOOTSTRAPPED` bypasses, cache-topology changes, or a
  new lock manager.
- Foreign Work Lane mutation, remote publication, hosted-CI success, and
  historical session or local-state rewriting.
