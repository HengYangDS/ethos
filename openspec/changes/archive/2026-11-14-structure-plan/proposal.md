# Proposal

## Why

The owner asked on 2026-11-13 for one semantic organization of every governed repository, enforced
as a constraint of the common base, so that arbitrary, flat and unordered trees stop appearing.
DR-0012 and DR-0011 leave product structure, test organization and documentation subject layout to
each repository, so no owner can judge a tree today, and ETHOS's own tree shows the result: one
undeclared root, 23 single-file directories and 302 loose files beside subject directories.

A committee of three seats approved a design after four review rounds, and the owner decided its
three open items on 2026-11-14: the width rule stays a count, the name list goes to the shared gate
of the common base, and one sentence of the product design contract is approved. The order was
decided with the direction: report first, refuse a new gap one release later, block stock after
0.2.0. A new direction queues behind the release-candidate path, so no Change of this design carries
code before 0.2.0, and DR-0026's gate gains no row. This Change is row 0 of the design's order, the
plan, which may land without code in beta.11 to beta.13. It lands after `rc-scope-plan`, which takes
DR-0026, and it puts the decision and the design in their tracked owners before any row opens.

## What Changes

- DR-0027 records the decision: three invariants, seven rules with the width rule a count and the
  name rule not built, the order of report, refusal and arming, the standing texts that it succeeds
  and narrows, and the contract sentence that the owner approved.
- This Change's design carries the approved design: the model, each rule's text, ETHOS's own stock,
  the repair, the seven later Changes with their estimated cost, and their order.
- The decisions README indexes the record.
- This Change implements nothing. It changes no code, test, specification or contract text. The
  Change that ships the first rule applies the approved contract sentence with its specification
  delta, so the contract never states a structure that the paradigm does not yet judge.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The record and the design change no requirement, so `skip_specs: true` applies. The later
Changes bring the deltas that the design's section 12.1 lists, in `repository-paradigm` and
`repository-governance`.

## Impact

- `docs/decisions/dr-0027-common-semantic-structure.md` and `docs/decisions/README.md`.
- Every later Change of the design cites DR-0027 for its rule and this design for its place in the
  order.
- No governed repository sees a changed verdict until the report Change lands, after 0.2.0.
