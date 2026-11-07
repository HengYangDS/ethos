# Proposal

## Why

The 2026-11-07 expert committee's resolution sets the gate for the first 0.2.0 release candidate
(§7) and requires, under R6, that the plan live in its owners now
(`build/runtime/work/committee-20261107/resolution-r3.md`). Four gaps remain:

- The terminal plan owns dependency order (`docs/plans/terminal-governance-product-design.md:49`),
  but it names no 0.2.0 RC order.
- The seven designs that realize the gate converged on 11-07 under `build/runtime/work/`, which Git
  ignores (`.gitignore:5`). No hosted check, reviewer or later lane reads them there, and the plan
  forbids a temporary file to become an active backlog (`:432-437`).
- The defect register of 11-05 (`build/runtime/work/beta2/essential-fixes-20261105.md`) still holds
  rows that no Change owns.
- `fast-tier`, `test-tiers` and `release-prepare` have no owner, kit-created Keychain items have
  none, and the 11-05 channels decision has no record number, since its planned DR-0018 is taken.

## What Changes

- The terminal plan gains a short section, `0.2.0 Release Candidate Order`, that names eight
  families in dependency order and cites this Change's design for each family's Changes, sizes and
  dependencies.
- This Change's design records that order with every Change, its size in line-equivalents and its
  dependencies; the owners of R6's items; where the resolution amends a draft; seven appendices that
  condense the converged designs (operation catalog, pre-tag release rehearsal, `github-pin` step 2,
  store retention, lane retirement residue class, peer identity records and history rebuild map),
  each keeping every decision, Change and acceptance; and an appendix that maps every register row
  to its owner Change, a 0.3.0 or host owner, its closing commit, or its withdrawal.
- After archive, each implementing Change cites its appendix of this design and carries its own
  proposal, design, spec deltas and acceptance. The register retires, and its ignored copy is
  deleted.
- Out of scope: every implementation, specification, test and budget change; designs for the
  families that no draft covers; the channels decision record, which is its own Change in the first
  family.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only the terminal plan and this design change, so `skip_specs: true` applies.

## Impact

- `docs/plans/terminal-governance-product-design.md`: one new section of about 45 lines under
  `Current Convergence Boundary`.
- No code, test, specification, schema or budget change; 0 line-equivalents.
- Later Changes: each Change of the order cites its appendix of this archived design.
- Adopters: no change.
- `build/runtime/work/beta2/essential-fixes-20261105.md` retires after archive (Workflow follow-up).
