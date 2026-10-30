# Proposal

## Why

`per-file-ceiling-parameters` lowered the Markdown ceiling to 500 nonblank lines. Its task 3.1
recorded that docs health found no length gap in ETHOS's tree, and its design's fleet preview listed
ETHOS with no Markdown document above 500. Both checks called docs health without the observed
document origins that the native audit passes. Docs health then stopped at
`docs_metadata_invalid:docs/_meta/taxonomy.toml:retained_origin_unobserved` before it measured any
length, and returned no length gap.

The landing preview of the lane head `e67c19ac6` measures correctly and blocks on two current
documents: `docs/governance/product-design-contract.md` with 510 nonblank lines and
`docs/reference/command-plane.md` with 512. Rerun with the observed origins, the fleet preview
changes only for ETHOS: the ten documents in four governed repositories stay as listed.

## What Changes

- The command plane's "Hidden Operational Roots" section becomes its own reference,
  `docs/reference/operational-roots.md`, which the command plane and the reference index route to.
- The Product Design Contract's "Documentation, Evidence, And Operational Resources" section no
  longer restates the documentation shape that the Docs Registry owns (entrypoints, directory
  READMEs and Decision Records); it routes to the Docs Registry. The edited section wraps at the
  repository's 100-column Markdown width.
- No requirement or measure changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The documents meet the ceiling that `per-file-ceiling-parameters` set; `skip_specs: true`
applies.

## Impact

`docs/governance/product-design-contract.md`, `docs/reference/command-plane.md`,
`docs/reference/operational-roots.md` and `docs/reference/README.md`. This Change records the
correction of the archived task 3.1 evidence and the ETHOS row of the archived fleet preview; the
archive itself stays as it was written.
