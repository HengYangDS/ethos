## Context

The official predecessor archive at
`openspec/changes/archive/2026-07-19-history-residue-closeout`
explicitly excludes real local-state effects and terminal budget settlement. A
later operator action produced immutable host-local receipts for the recovery
archive and exact maintenance apply. The current Work Lane has now integrated
candidate-owned APIs, but must still remove live campaign overages and complete
local lifecycle transitions.

## Goals / Non-Goals

**Goals:**

- preserve the predecessor archive and bind the later operator receipts without
  changing their historical HEAD;
- make the integrated state/schema implementation pass its public contracts;
- reach `python_product<=35675`, `python_tests<=46865`,
  `python_total<=84024`, `shell<=1552`, and `toml<=11633` without limit changes;
- prove the final tracked HEAD, archive the successor, land locally, close out in
  `maintainer_break_glass_local` mode, and align local main/dev/candidate;
- keep remote, hosted, r7, foreign, and unbound state outside mutation scope.

**Non-Goals:**

- claiming global campaign terminal completion while
  `terminal_target_met=false` or active debt remains;
- repeating the already-applied destructive maintenance operation;
- using repository evidence to claim current counts for ignored local state;
- probing or publishing to GitLab or any other remote.

## Decisions

### 1. The predecessor archive is immutable historical evidence

The stale active duplicate is removed. This successor uses a new logical ID and
future dated archive path. It references, but never edits, the predecessor
archive.

### 2. Real local effects are bound to exact external receipts

The maintenance receipt is historical evidence at
`fe774c994c5641b60f49a3e60a968ed8eba6fbee`. The carrier records its inventory,
receipt, archive, and recovery-snapshot digests plus deletion counts. Current
local leases and proofs may have changed since apply and are never inferred from
those historical counts.

### 3. Budget settlement uses measured deletion only

The authoritative gate is `ethos quality source-budget --json`. Every listed
campaign growth overage must reach zero. Baselines, limits, active debt, and
terminal targets remain unchanged. Global terminal completion is a separate
claim and is not made here.

### 4. Archive precedes promotion effects

All task checkboxes end at successor archive. Candidate land, external
control-replacement verification, accepted-root closeout, local ref alignment,
publish readiness, and owned-lane retirement are post-archive operational
receipts so archive completeness is not circular.

### 5. Closeout is local and narrowly authorized

The final closeout mode is `maintainer_break_glass_local`. It may update only the
local accepted/candidate refs required by the governed command. Remote actions
are deferred/unclaimed; r7 and foreign/unbound lanes remain observe-only.

## Risks / Trade-offs

- **Compression removes behavior** -> require focused tests followed by the full
  suite and 100% branch coverage.
- **Historical effects are mistaken for current state** -> label receipt HEAD,
  observation time, and source-absence checks separately from current inventory.
- **Control changes self-attest** -> require an external control-replacement
  receipt outside the candidate tree before accepted closeout.
- **Candidate advances again** -> reobserve and use only a governed, explicitly
  authorized local integration path; never hand-rebase.

## Migration Plan

1. Replace the stale active duplicate with this successor and bind a new claim.
2. Reconcile integrated state/schema behavior and preserve focused test evidence.
3. Remove all five live source-budget overages without changing policy values.
4. Run complete tests, coverage, types, owner gates, claims, and strict OpenSpec.
5. Refresh and commit generic parity, update the Chronicle/claim digest, and run
   final HEAD-bound executed proof.
6. Archive the successor, then perform local candidate land, external control
   replacement, maintainer break-glass accepted closeout, ref alignment, local
   publish readiness, and owned-lane retirement.

## Open Questions

None. The effect boundary, numerical limits, remote deferral, and closeout mode
are fixed.
