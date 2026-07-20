## Why

Official OpenSpec 1.6 reports a freshly created Change as `no-tasks` until its
first planning artifact is written. ETHOS excluded that official active state
from lifecycle selection, so an adopter could not create the one allowed
`scope.toml` companion needed to begin governed work.

## What Changes

- Treat official `no-tasks` Changes as active, non-complete lifecycle carriers.
- Preserve selection precedence: `in-progress` remains preferred, followed by
  `no-tasks`, then archiving and complete records.
- Admit the existing exact-one untracked `scope.toml` bootstrap only for a
  selected `no-tasks` Change; ordinary material paths remain fail-closed.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=openspec-no-tasks-scope-bootstrap; reuse=extend; change=modify; facet:lifecycle=authoring,validation; facet:surface=openspec,source,test; facet:authority=source,test,openspec. Align selected Change lifecycle states with official OpenSpec so governed scope bootstrap is possible without widening material writes.

## Impact

The OpenSpec lifecycle adapter and focused regression tests change. The
repository-governance specification gains the formal scenario. No session
store, credential, provider route, hosted runner, or foreign Work Lane changes.

## Out of Scope

- Treating a `no-tasks` Change as lifecycle-complete or bypassing proposal,
  design, task, delta-spec, claim, validation, or proof requirements.
- Admitting ordinary material writes, an unrelated Change, more than one scope
  bootstrap, or a malformed/tracked scope companion.
