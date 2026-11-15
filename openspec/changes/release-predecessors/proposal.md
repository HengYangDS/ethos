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

This row of the gate owns the set, the support window, the classes of a predecessor and the carrier
that states them (the archived `rc-plan` design, B.3).

## What Changes

- The subject set is a reading of trees and never a number in a record: the count of readable
  governed repositories inside the support window that take the release.
- The support window is measured from the last landed bump.
- The waiver for the frozen repository names its shape and its runtime, and no repository by name.
- The weekly page's measure of pins in reads its total by this definition.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The distribution specification's requirement on the releases a beta's journey starts from, the
release guide and the weekly page. It adds no rule for a governed repository. A rule that a subject
declares no scheduled pipeline during the soak is a new rule and waits for the first reports after
the rule row.

Owner: the release lead. Next action: write the design with the measured count. Read again: at the
cut of 0.2.0-beta.12, 2026-11-19.
