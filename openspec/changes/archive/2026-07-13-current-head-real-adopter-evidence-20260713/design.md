## Context

An existing ETHOS adopter has its own profile, skills, OpenSpec carriers,
repository-native proof gates, and a native `pixi run ethos` command. A local
isolated clone can therefore test the product command plane without mutating
its source checkout or pretending that a generic overlay may replace its
already-owned governance surfaces.

## Decisions

### Existing governance surfaces must refuse replacement

The generic overlay plan exposes nonempty `.ethos` and skills surfaces as
conflicts. The authorized apply is expected to remain blocked: this is the
safe result, not a failed attempt to hide. The Chronicle records that no
adopter governance file was overwritten.

### Compare external and native command surfaces

The observed product runtime invokes eight read-only workflow/reporting
commands against the isolated adopter root. The adopter's declared native
`pixi run ethos` command executes the same eight commands. The observation
records only semantic result parity and false-negative count, not semantic
correctness of either system.

### Keep raw material local and redact local identities

The raw JSON bundle is outside the repository. The tracked Chronicle includes
only product/adopter revisions, checksum, counts, bounded outcomes, and
negative authority statements. No local paths, account names, raw command
streams, credentials, or adopter content are promoted.

### Documentation is routing, not a parallel truth root

`docs/evidence/` and `docs/history/` receive one curated link each. The claim
and Chronicle remain the canonical evidence record; the documentation index
copies neither raw payload nor current-state evidence.

## Risks / rollback

Matching command results do not establish semantic compatibility, hosted
execution, authority, or independent review. Revert this carrier, claim,
Chronicle, and documentation links to remove the observation. The adopted
source checkout and all remote state remain untouched.
