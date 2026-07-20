## Why

`work/owner-recovery-hook-probe-20260720` is a duplicate unbound
accepted-ancestor residual. Its one-file parity projection is historical and
superseded by later accepted parity evidence. Leaving the ref open preserves a
dead namespace object; deleting it without exact authority would be unsafe.

## What Changes

- Record exact graph-backed absorption for one clean, lease-free, unbound source
  ref, distinguishing provenance retention from stale evidence reuse.
- Bind one accepted Claim and Chronicle to a later native `lane retire unbound`
  transition for that target only.
- Require exact head, accepted policy bytes, authorization, break-glass,
  irreversible confirmation, re-observation, compare-and-delete, and receipt.
- Retire this temporary carrier after the target receipt exists.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=owner-recovery-hook-probe-retirement;
  reuse=extend; change=modify; facet:lifecycle=retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=source,graph,evidence,native-command.

## Out Of Scope

Any target other than `work/owner-recovery-hook-probe-20260720` at its exact
observed head; an active lease; raw deletion; worktree reconstruction; protected
branches; remote or hosted CI mutation; and publication.
