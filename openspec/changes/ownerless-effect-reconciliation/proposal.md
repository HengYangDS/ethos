## Why

Three clean post-lease ownerless lanes are semantically absorbed, but their Git
heads remain diverged from accepted truth. The native `retire` decisions were
recorded correctly and then produced zero effect because WCP admits only an
accepted-ancestor source. Bypassing WCP would violate the accepted closeout
contract; retaining the lanes indefinitely would also leave obsolete worktree
residue.

## What Changes

- Record the exact no-effect WCP result for all three clean ownerless lanes.
- Keep the original semantic rejection of their historical implementations.
- Authorize transient `preserve-retire` only as a content-addressed bridge when
  direct clean retirement is blocked by the accepted-ancestor WCP boundary.
- Bind the existing dirty package to an exact manifest clear decision.
- Archive and accepted-close this authority carrier before native effects run.
- Use a separate exact-manifest successor carrier after effects to authorize the
  three clean package clears and final housekeeping.
- Leave every valid-owner lane observe-only.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-effect-reconciliation;
  reuse=extend; change=modify; facet:lifecycle=retirement,recovery,validation;
  facet:surface=openspec,claim,chronicle,evidence;
  facet:authority=git,evidence,test,native-command.

## Out Of Scope

Weakening or bypassing WCP, raw Git deletion, replaying rejected historical
implementation, taking over any valid-owner lane, keeping convenience archives,
remote publication, hosted-CI claims, or clearing any package without its exact
accepted manifest binding.
