# Proposal

## Why

The release candidate needs every subject bumped to the frozen beta and 72 hours since the last
bump (DR-0029). The archived `rc-scope-plan` design counts those subjects as eleven adopter pins.
The number is wrong in both directions. One governed repository is frozen on its runtime by its
owner's decision, and two repository families are under repair and cannot pass a proof yet, so a
condition that counts them never reads true.

The owner decided the set on 2026-11-15. The condition counts a governed repository that the
releasing host can read, that is inside the support window and that takes the release. The frozen
repository is a waiver that names a shape and a runtime. The two families under repair migrate in
their own lanes; they are no prerequisite of the candidate or of the older selector form's
retirement.

This row of the gate owns the set, the support window, the classes of a predecessor, the carrier
that states them and the operation that derives it: appendix B.3 of the archived `rc-plan` design
and Change 3 of its B.8. The archived `rc-scope-plan` design places the row in the batch of
2026-11-28.

Today a release's predecessors are named by hand in a dispatch input, from memory of what each
governed repository selects. Nothing derives them, nothing records them, and the paradigm reports
any key of the release table but the mirror as unread.

## What Changes

- The subject set is a reading of trees and never a number in a record: the governed repositories
  that the releasing host can read, that have selected a runtime of the product, with or without
  a tracked pin, and whose last landed bump is inside the support window.
- The support window is 14 days, measured back from the newest landed bump among the subjects
  read. A bump is read from the accepted branch's own history; a subject without a pin has none
  and is inside the window.
- A release upgrades from the previous release and from every release that a subject inside the
  window pins or has selected. Each carries its class from the pin module's data.
- The release binding records that set under `[release.upgrade_from]`, release by release with its
  class. The table names no repository and holds no count of them. The paradigm reads the key.
- `ethos lane upgrade-from` derives the set offline for the committed release, reports each
  subject's accepted head, pin, selection and last bump without its path, and blocks when the
  record is empty or lacks a derived release. Its result counts the subjects by pin form and by
  selection alone, and for each release the subjects that name it.
- DR-0030 records the candidate's subject set and the waiver for the frozen repository. The
  waiver names a shape and a runtime, and no repository.
- The weekly page's measure of pins in reads its total by this definition.

The refusal at the release tag and the reading in `status` are not in this Change. The drafts
`release-predecessors-binding` and `upgrade-path-status` hold them.

Not breaking. No command changes its result for a tree that declares no such table, and no tree
that passed the paradigm declares one, because the paradigm reported the key until now.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the requirement on the releases that a beta's journey starts from defines the
  subject set and the support window, and a new requirement states the record and the operation.
- `repository-paradigm`: the requirement on the release table's keys admits `upgrade_from`.

## Impact

`src/ethos/repository/release/predecessors.py` and `src/ethos/adapters/repo/upgrade_from.py`, both
new; the pin, changelog and branch-role modules; the lane repair operations and their catalog rows;
the gap registry; the release guide and `CHANGELOG.md`; the decision record DR-0030 with its
entry in the decisions index.

It adds no rule for a governed repository. The three new gaps are raised only by the new operation,
which a caller runs in the product's own release lane. A rule that a subject declares no scheduled
pipeline during the soak is a new rule and waits for the first reports after the rule row.
