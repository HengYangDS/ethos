# Proposal

## Why

A proof binds the commit: its working content and its index equal the commit's tree before and after
its gates. It does not bind the repository's local Git state.

One case of it was a regression of 0.2.0-beta.11 and is repaired there. Measured on 2026-11-17 with
one probe at two commits, each with its own product code, on a committed document with two
misspellings: at `v0.2.0-beta.10` the prose gate blocks as committed, with one line in the Git
directory's local attributes file that marks the document `linguist-generated`, and with the line
removed; at the release head of 0.2.0-beta.11 it blocks, passes and blocks, with the source binding
true each time. The cause is that release's own fix which leaves a vendored or generated path out of
every authored selection. The owner decided on 2026-11-17 that the release repairs it before its
tag: while the local attributes file names a received attribute, the authored selection takes no
received mark. That repair is the Change `authored-selection-local-attributes` on the release head,
not this one.

What stays is older than that release and is this Change's subject. Read in the code at
`v0.2.0-beta.10` and not run: the text selection's preserved set, the paradigm audit, `ethos status`
and the commit hook's staged size and text checks take received paths from the same attribute
reader, so a local attributes line also reaches them, in that release and since.

Two more measures of the same day, from the design study of `gate-reuse`, go in the safe
direction: an ignored cache directory at the root blocks the generated-artifact check, and a
residue name that the local exclude file ignores fails the hygiene check.

Counted on the releasing host on that day: of 31 governed checkouts, none holds an effective line
in its local attributes file, and 16 hold effective lines in a local exclude file.

The owner decided on 2026-11-17 that reading unbound local state is a defect: 0.2.0-beta.13 reports
the state, and whether a proof refuses it is decided for 0.3.0.

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

The attribute reader (`src/ethos/adapters/repo/git_attributes.py`) and its older callers, and a
proof's result. Not measured: a whole proof run with such a line (one gate's verdict is measured),
the older callers' answers, Linux and Windows, and a governed repository's own proof.

Owner: the release lead. Next action: the design with the batches of 0.3.0. Read again: when the
batches of 0.3.0 are planned.
