# Proposal

## Why

`release-predecessors` records what a release upgrades from under `[release.upgrade_from]` and
derives the set with a read that blocks nothing. A release can therefore be tagged while its
record is empty or lacks a release that a subject still pins or has selected. The archived
`rc-plan` design, appendix B.3, asks that `land --release` re-derive the set offline and refuse an
empty or incomplete one. The release lead ruled on 2026-11-15 that this part leaves
`release-predecessors`, which had reached its size.

`land --release` with a tag is the tagging path of every governed repository. A refusal for a
release binding that declares no such table would be a new rule for each of them, which the law
freeze of DR-0029 does not admit.

## What Changes

- `land --release` with a tag re-derives the set offline, as the read of `release-predecessors`
  derives it, and refuses when the committed record is empty or lacks a derived release.
- The refusal binds only a release binding that declares the table. A repository that tags
  without the table is not read and not refused, so this is no new rule for it.
- It takes effect for the product when its own release binding records the table, in a lane
  whose selected runtime reads the key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The release promotion and its regressions, and the distribution specification's requirement on
what a release records. A sketch of the call measures 7.6 product line-equivalents. Its
regressions need the release fixture with a declared record and are estimated at 50 to 70 test
line-equivalents; that figure is not measured. The refusal is new on the product's own release
path and can stop only a repository whose release binding declares the table.

Owner: the release lead. Next action: write the design with the measured sizes. Read again: at the
cut of 0.2.0-beta.13.
