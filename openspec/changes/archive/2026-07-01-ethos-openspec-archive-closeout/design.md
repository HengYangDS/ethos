## Context

The terminal product design defines archive as a product closeout operation.
Official OpenSpec owns the archive command and spec merge semantics; ETHOS owns
the repository product checks around closeout readiness, claim/evidence
binding, and Work Lane sequencing.

The useful reference-adopter pattern is an archive audit as part of closeout proof,
not a second command plane. ETHOS narrows that pattern to product duties:
directory identity, metadata presence, complete task state, and scoped delta
spec shape. It intentionally avoids adopting reference-adopter domain vocabulary or
retroactive formatting requirements that would rewrite historical narratives.

## Design

`completed_active_changes_report` remains the closeout package consumed by
`ethos land` and `ethos land --closeout`. It now composes two checks:

- official OpenSpec list status for completed active changes that still need
  archive;
- ETHOS archive closeout report for archived change metadata, tasks, and delta
  shape.

The archive report is read-only. It does not run `openspec archive`; maintainers
or Work Lanes still call the official tool for archive mutation. Its job is to
block land/closeout if the archive state is structurally untrustworthy.

## Proof Strategy

The RED test creates a repository where official OpenSpec list is clean but an
archived change lacks metadata and has incomplete tasks. The expected product
state is blocked. The GREEN implementation adds the archive closeout report and
wires its required gaps into the existing closeout lifecycle package.

This lane also archives the two prior campaign carriers with official OpenSpec
commands, then updates their claims to point at the dated archive paths.
