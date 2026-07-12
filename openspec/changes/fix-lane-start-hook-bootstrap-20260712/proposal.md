## Why

`ethos lane start --apply` creates a fresh Work Lane through Git's
`reference-transaction` hook.  On a new non-accepted worktree the hook currently
tries to materialize a complete Python environment before there is a lease or a
work-lane transition to evaluate; with the remote temporarily unavailable, that
bootstrap can wait on an empty nested cache and leave the new worktree locked in
initialization.

The accepted-root guard must remain fail-closed, but ordinary Work Lane creation
must retain its documented fail-open behavior and must not require a network or a
pre-existing runtime merely to create the lane that will own later work.

## What Changes

- Make the reference-transaction hook skip the lazy Python bootstrap only for a
  fresh `work/*` branch whose checkout-local runtime is absent.
- Keep the existing hook evaluation for an accepted branch, and for non-accepted
  branches once a runtime exists, so accepted admission and Work Lane lease-head
  repair remain unchanged.
- Add a regression contract for the fresh-worktree fast path.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: a fresh Work Lane ref creation is not
  blocked by runtime materialization, while accepted-root admission remains
  fail-closed.

## Impact

- `.githooks/reference-transaction`
- `tests/unit/cli/test_hooks_runtime.py`
- Repository-governance OpenSpec requirements
