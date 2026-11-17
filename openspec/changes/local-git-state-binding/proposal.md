# Proposal

## Why

A proof binds the commit: its working content and its index equal the commit's tree before and
after its gates. It does not bind the repository's local Git state. Measured on 2026-11-17, at the
release head of 0.2.0-beta.11 and at the head of the batch of 0.2.0-beta.12, with one probe in a
scratch repository: a line in the Git directory's local attributes file that marks a tracked
document `linguist-generated` keeps the source binding true and takes the document out of the
selection of authored files. Read in the code and not run end to end: the Markdown, prose, link,
configuration and source-format gates, the paradigm audit, `ethos status` and the commit hook's
staged checks read that selection, so none of them then reads the document.

Two more measures of the same day, from the design study of `gate-reuse`, go in the safe
direction: an ignored cache directory at the root blocks the generated-artifact check, and a
residue name that the local exclude file ignores fails the hygiene check.

Counted on the releasing host on that day: of 31 governed checkouts, none holds an effective line
in its local attributes file, and 16 hold effective lines in a local exclude file.

The owner decided on 2026-11-17 that this is a defect. The entry of 0.2.0-beta.11 names it among
the known open defects, 0.2.0-beta.13 reports the state, and whether a proof refuses it is decided
for 0.3.0.

## What Changes

The report is decided. The refusal is a candidate for the design:

- In 0.2.0-beta.13 a proof's result and the gate-input record of `gate-reuse` hold the count of
  effective lines of the local attributes file, and each gate's input key holds Git's attribute
  classification of the committed paths.
- For 0.3.0, one of three ways: a proof refuses a local attributes line that names a received
  attribute; the selection of authored files reads the tracked attribute files alone; or the
  state stays a reported boundary. Under DR-0029 a refusal needs an earlier release that reported
  it, which the item above gives.
- The keys of Git's configuration overlay that reach local Git are a sibling question. The design
  of `gate-environment` gives it a Change of its own.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The selection of authored files (`src/ethos/adapters/repo/git_attributes.py` and its callers) and
a proof's result. Not measured: a proof that passes wrongly end to end, any release before
0.2.0-beta.11, Linux and Windows, and a governed repository's own proof.

Owner: the release lead. Next action: the end-to-end measure, then the design with the batches of
0.3.0. Read again: when the batches of 0.3.0 are planned.
