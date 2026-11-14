# Proposal

## Why

DR-0021 binds the 0.2.0 release candidate to the committee resolution of 2026-11-07, and the
`rc-plan` design cites that resolution's items by number. The resolution itself was never tracked,
so no tracked text states what the gate requires, and its rule that an item blocks "until its
acceptance holds or a recorded owner decision waives it" had no place to record a waiver.

A review of the 51 open rows of the order against the gate's own words found 42 required or
cost-lowering rows, and two review seats rejected its first draft before a second one passed a
verifier. The owner decided on it on 2026-11-14, in these words: `按照你建议的方式`. That decision
holds three waivers, the choices for six rows without gate text, four weekly batches and the dates.
The resolution's item R6 asks that the plan lives in its owners; this Change puts the gate, the
waivers and the order there. It is the row "the gate's tracked text" of the first batch.

## What Changes

- DR-0026 records the gate by shape, the three waivers with what stands in for each, the rows that
  leave 0.2.0 and the dates.
- This Change's design orders the kept rows in four weekly batches, with the breaking changes, the
  method, the three outcomes the release is judged by, and the budgets.
- The terminal plan's release candidate section points to DR-0026 and to this design, and the
  decisions README indexes the record.
- This Change implements nothing else; each row opens as its own Change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The record and the order change no requirement, so `skip_specs: true` applies. The Changes
that carry the waivers' effects bring their own deltas: the MCP preview guard and the surface
texts.

## Impact

- `docs/decisions/dr-0026-release-candidate-gate.md`, `docs/decisions/README.md` and
  `docs/plans/terminal-governance-product-design.md`.
- Every later row cites this design for its batch, and every later waiver is a successor record of
  DR-0026.
