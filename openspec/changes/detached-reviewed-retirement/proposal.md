## Why

A registered detached worktree has content and Git administration state but no
branch to delete. Reviewed-content retirement currently requires a topic ref,
so an already adjudicated historical worktree cannot leave through the public
protocol without manufacturing a branch or bypassing admission.

## What Changes

- Select a detached registered worktree by its exact absolute path through
  existing reviewed-content abandonment.
- Bind its detached HEAD, native registration, content and index to the existing
  receipt. Derive effects only for resources that actually exist.
- Preserve stopped-writer coordination, current actor, accepted-object checks,
  content drift rejection and resumable native removal.
- Keep unrelated refs, Leases and detached worktrees unchanged; create no
  temporary topic, synthetic Lease or parallel cleanup protocol.
- Verify the native observer under one unprivileged Linux job identity;
  replace the incomplete pytest-only identity drop at the existing CI entrypoint.

## Capabilities

### Modified Capabilities

- `repository-governance`: receipt-bound retirement of reviewed detached
  worktrees without inventing a ref-deletion effect.

## Impact

Existing retirement contracts, selection, effect compilation, observation,
CLI projection, regression tests and the native Linux verification prerequisites;
canonical execution-plan updates.
No supply upgrade, network reconfiguration, signing repair, general Lease
redesign, adopter mutation or whole-repository layout change.
