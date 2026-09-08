## Why

A clean historical topic can be entirely retained by another local ref while
neither ref has entered accepted history. The current retirement owner requires
a leased authoring successor, so duplicate checkouts cannot be retired without
reviving obsolete authoring policy. Retaining commits and accepting semantics
are different obligations.

## What Changes

- Extend the existing `lane retire superseded --absorbed-by` input to accept an
  exact local branch ref that preserves every target commit.
- Admit deletion-only retirement from the accepted control root with an explicit
  actor and authorization, clean exact target, and admissible target Lease.
- Bind the retained ref and its observed OID in the existing Git effect assertions;
  reject drift before worktree removal and in the atomic ref transaction.
- Keep shared retirement receipts, recovery, hooks, and post-observation; introduce
  no new command, branch, state store, compatibility carrier, or accept claim.
- Apply the user's revised convergence constraint in the existing source-budget
  owner: product and tests each have a 40000-ELOC ceiling; other categories and
  the project total remain observations. Separate generated output and archive
  records without changing handwritten-source measurement or coverage policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: clean redundant local topics may retire while their
  complete Git history remains reachable through an exact surviving local ref.
- `quality`: enforce explicitly declared maintenance budgets rather than forcing
  a heterogeneous aggregate threshold.

## Impact

The existing linked-retirement admission, effect compiler, ref-policy projection,
CLI guidance, regression tests, product contract, and terminal plan change.
The explicitly requested budget adjustment changes the native format declaration
and its existing measurement contract; it creates no additional quality owner.

Out of scope: discarding dirty content, retiring the sole surviving reference,
accepting old product semantics, remote deletion, supply upgrades, historical
configuration migration, and new authoring permission.
