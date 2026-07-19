## Why

One visible `work/*` ref is lease-free, unbound, and an ancestor of accepted
`dev`. Its useful behavior is already absorbed, but native exceptional
retirement correctly refuses deletion until the source has accepted,
target-specific policy evidence. Leaving it indefinitely conflates retained Git
history with an active operational surface.

## What Changes

- Add an accepted local evidence carrier for one exact ownerless unbound
  accepted-ancestor residue.
- Add one active Claim and Chronicle so the later native effect is bound to its
  exact branch and head.
- Record that separately observed leased unbound refs remain protected and are
  outside this carrier.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=exceptional-unbound-target-evidence;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,archive;
  facet:surface=docs,openspec,evidence; facet:authority=source,docs,openspec,
  claim,chronicle. Clarify that one accepted target evidence only authorizes
  a later single-ref transition.

## Impact

Affected surfaces are local documentation, OpenSpec, Claims, and Chronicles.
No runtime delete behavior, remote, hosted CI, or foreign lane is changed.

## Out Of Scope

- Adding a batch retirement command, changing the native exceptional transition,
  raw Git or state deletion, force worktree removal, or lease takeover.
- Mutating a diverged, dirty, linked, leased, foreign, or otherwise unlisted
  Work Lane.
- Remote push, GitHub or GitLab reconciliation, hosted CI, or any publication
  claim.
