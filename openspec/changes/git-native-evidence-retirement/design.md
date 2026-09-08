## Context

The selected Attestation set is an independent Git ref with a deterministic
object tree. Its internal `evidence/attestations` member path is not a worktree
directory. Current proof validates selected predicates and exact bindings. The
historical topology provider instead requires a physical directory and counts
records; its freshness wrapper checks only that topology verdict.

At source `06ea14f0ae9cfdf1e760ff8dc944b22c0b22361c`, the root historical
tree `a77f77462c487a7a9b7746f3e93b4bbdad8f51ce` contains 556 tracked files.
`docs/evidence` contains only a README duplicating the existing provenance
explanation. Current code and declarations mandate both obsolete surfaces.

## Decision

Keep the existing Attestation set and operation-specific proof consumers as
the only current proof mechanism. Remove the topology/freshness provider,
declaration and packaged resource rather than return unconditional success or
introduce another evidence service. Retire unused profile evidence roots and
the candidate collector that has no production caller; preserve safe normative
source declarations as intent metadata, distinct from proof selection.

Delete the historical worktree copies after exact tracked-content comparison.
Git preserves every byte under the stated source commit and tree. Archived
OpenSpec references remain dated historical statements, not live path readers.
Current links use historical Git coordinates where retrieval is useful; unique
current obligations belong to their existing specification or product owner.
Historical preservation-package records do not authorize deleting any packages
or lanes in this Change. Neither the selected Attestation ref nor its member
layout is changed.

The existing provenance explanation owns the useful documentation semantics.
Remove the redundant README, required path and empty directory. Remove the
retired roots from formatting, budget and generated-output declarations rather
than add a forbidden-path blacklist. Ordinary source classification applies
again to any newly introduced files at those paths; official OpenSpec archive
accounting remains distinct.

## Verification And Delivery

Regressions exercise default profile semantics, source-budget accounting and
proof-floor membership. Real Git tests demonstrate that historical workspace
content cannot select an Attestation and that current set read/write needs no
workspace evidence root. Existing exact-proof and malformed-set tests preserve
the security boundary. Source/docs references, package resources and official
specification deltas close together. Focused checks precede exact full proof,
archive, acceptance and immutable runtime readback. Root deletion in the owned
Work Lane is not accepted-root deletion or deployed completion.
