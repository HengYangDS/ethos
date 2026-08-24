## Context

The installer already selects one immutable runtime from the invoking
repository. Its repository-family post-observation nevertheless calls
`hook_runtime_binding()` independently for each linked worktree. Without an
explicit expected identity, that reader reloads each checkout's historical
profile and schema. A stale checkout can then make a valid common activation
unobservable.

## Decision

Resolve `RuntimeSourceIdentity` once from the invoking repository authority,
before materialization and Git-config mutation. Pass that exact value to every
post-observation, including the final root binding. Linked worktrees remain
independent filesystem/configuration observations, but cannot reinterpret the
source identity.

## Non-Goals

- Supporting historical profile schemas.
- Ignoring unreadable worktree configuration or runtime files.
- Adding a fallback, alias, migration reader, or second identity carrier.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Common activation uses one runtime source authority` | `2.1` | stale linked-profile installation regression in `tests/unit/cli/test_hook_runtime.py` |
