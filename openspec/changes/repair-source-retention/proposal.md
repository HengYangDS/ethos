# Proposal

## Why

A history repair replaces commits beneath accepted history and leaves a record in the retained
attestation set. The record stays for good. Every later question whether an older commit was
absorbed walks the completed repairs beneath accepted history and validates each one again from
its source commit: the old head, and for a history repair each corrected commit. Nothing in the
repository holds that source. The record names a backup bundle at a path that the operator
chose, which no later command reads, and Git prunes a commit that no ref reaches.

Measured on 2026-11-19 in this repository, with the engine of the head that 0.2.0-beta.11 tags:

- One of three repair records, of 2026-09-16, named an old head and 40 corrected commits. The old
  head and 19 of the 40 were absent from the object store. Its bundle had been written inside a
  worktree that was retired later. The two later repairs validated, because refs made by hand
  hold their old heads.
- With that source absent, the retirement of two proposal refs whose head a base refresh had
  rewritten was refused on both forges. The draft `refusal-repairs` has carried that refusal and
  its misleading code since 2026-11-16; this draft is about why the source can be absent at all.
- One of the two forges still served the old head by its name. Fetched into a scratch repository,
  checked against the record and then held by one ref in the repository, it made all three
  records validate, and both retirements passed.
- One answer of the walk took 101.8 seconds with three repairs. 95.7 of them were 58 signature
  verifications, each started on its own, and nothing is kept for the next answer: one
  retirement took 428 and 462 seconds on the two forges.
- A fixture repository shows the same end to end: two repairs, the later one's source held by a
  ref, a pruning, and the question about a head that no repair maps is refused where it had
  answered before.
- A census of 15 governed checkouts on the releasing host found 8 repair records in 5
  repositories. Four records in three repositories kept their old head only as an unreachable
  object, one pruning from the same state. Their keepers were told the one command that holds it.

## What Changes

Candidates for this row's design, none decided:

- A repair holds its own source: the transaction that moves the refs also writes a ref of the
  product's namespace for the old head, so that the store that keeps the record keeps what the
  record needs to be validated again.
- A report names every completed repair whose source no ref holds, with the command that holds
  it, and names a source that is already absent as absent.
- The walk verifies each repair once for a command and for the apply that follows its probe.
- A question for the owner before the design, because it changes a behavior that fails closed
  today: whether a repair that cannot be validated stops every question that walks past it, or
  only the answers that would rest on it.

Not sized. A slice enters a batch only with a failing case first; the fixture case above is the
start of it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None yet. The design names the requirement on history repairs that gains the retention, so
`skip_specs: true` applies to this draft.

## Impact

The history repair's transaction, the validation of a completed repair, the conservation walk
and a report, with their tests. No repository's existing records change.
