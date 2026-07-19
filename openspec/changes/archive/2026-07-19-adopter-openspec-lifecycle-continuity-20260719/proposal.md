## Why

The historical Work Lane for the adopter OpenSpec lifecycle episode no longer
has its original host worktree. Its archived OpenSpec carrier, active episode
claim, committed implementation, session stream, and shell snapshots remain
observable, but the original checkout-local runtime and temporary proof
artifacts do not. Continuing from an old branch or reconstructing that host
directory would confuse historical evidence with current authority.

## What Changes

- Create an owned successor carrier bound to the existing
  `adopter-openspec-lifecycle-20260714` episode claim.
- Record a loss-bounded continuity packet: retained inputs, their identities,
  irrecoverable runtime state, current baseline, and replay boundary.
- Re-prove the current generic-adopter lifecycle behavior on a successor HEAD
  rather than promoting historic proof as current proof.
- Add the repository-governance requirement for loss-bounded successor
  continuity when a historical Work Lane cannot be resumed in place.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=loss-bounded-successor-continuity;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,archive;
  facet:surface=openspec,evidence,claim,chronicle; facet:authority=source,test,
  openspec,claim,evidence

## Impact

- `openspec/specs/repository-governance/spec.md`
- The active episode claim and a successor continuity Chronicle.
- A current-lane re-execution of the existing adopter lifecycle regressions and
  ETHOS/OpenSpec lifecycle gates.

## Out Of Scope

- Reconstructing the missing historical Codex worktree or temporary directories.
- Editing historical JSONL, SQLite, archived carrier contents, or foreign Work
  Lanes.
- Whole-branch merge or cherry-pick of the historical Work Lane.
- Remote publication, hosted CI, or a claim that historic runtime state was
  restored.
