## Why

An absorbed local ref can be impossible to retire solely because it does not
use the authoring `work/` prefix. The installed runtime rejects the observed
`codex/openspec-19-archive-owner` ancestor with `absorbed_ref_role_invalid`, even
though no worktree or Lease remains. Authoring permission and deletion of
absorbed local resources are different obligations.

## What Changes

- Admit exact deletion of absorbed local topic refs independently of their
  authoring prefix, using current accepted policy and fresh Git facts.
- Apply the same eligibility to explicitly selected clean linked worktrees.
- Keep accepted, release, and candidate resources outside this retirement path;
  preserve dirty content, Lease authority, exact-CAS and recovery boundaries.
- Make the installed reference-transaction transport consume the same admitted
  retirement rather than require the historical object to carry current policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: absorbed local resource retirement and its native
  hook admission must not depend on an authoring prefix.

## Impact

The existing branch-role value, retirement admission, reference-transaction
transport, focused tests, and command documentation change. No new schema,
registry, persistent authority, dependencies, or adopter-specific code is added.

Out of scope: deleting dirty overlays, abandoning unabsorbed semantics, Lease
takeover, remote review-ref retirement, test scheduling, and hosted network
repair. Historical semantic adjudication remains in the existing terminal route.
