## Why

`work/openspec-archive-logical-identifier-20260719` is a single unbound,
accepted-ancestor residue with an active lease owned by the current holder. Its
original archived OpenSpec carrier records the reader change, but it does not
bind the later destructive lifecycle transition that ETHOS deliberately
requires.

## What Changes

- Add one active Claim and Chronicle that bind only the target ref and immutable
  target head to a later native exceptional retirement.
- Add a minimal OpenSpec carrier that preserves the target-specific,
  vendor-neutral authority boundary.
- Clarify the canonical repository-governance requirement that a current holder
  may relinquish only its exact lease generation inside the native transition.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=openspec-archive-logical-identifier-unbound-retirement; reuse=extend; change=modify; facet:lifecycle=authoring,validation,closeout; facet:surface=openspec,evidence,claim,chronicle; facet:authority=source,openspec,claim,chronicle,native-command.

## Impact

Only local OpenSpec and evidence surfaces change. The native command is the
sole later effect; this carrier does not delete any ref or lease.

## Out Of Scope

- Batch retirement, raw Git/SQLite deletion, force worktree removal, foreign
  lease takeover, remote mutation, hosted CI, or vendor-specific identity
  authority.
- Mutation of the target's archived original Change or Chronicle.
