---
subject: ethos:provenance
role: explanation
state: canonical
relations:
  canonical_for: evidence attestation
---

# Provenance And Attestation

ETHOS evidence is designed to project into SLSA-style provenance and
Sigstore-compatible signing flows.

The terminal kernel durably persists Attestations. Commitment is compiled from
one exact official OpenSpec projection; Facts are freshly observed and
TransitionPlan is transient. Historical views are derived from Git, official
OpenSpec archives, and Attestations. Governance adapters may sign
Attestations, publish transparency records, or emit hosted CI artifacts, but
adapter output never replaces the repository evidence chain.

`ethos prove --json` emits a proof Attestation bound to the compiled Commitment
identity, exact HEAD, Facts digest, TransitionPlan digest, policy
digest, effect digest, and verifier boundary. It does not establish a release.
The canonical record is selected through `refs/ethos/attestations-set`; local
command output is a projection, not a second proof selector.

## Storage And Currentness

Current readers select Attestations from `refs/ethos/attestations-set` and
validate the required predicate and exact bindings. Its internal
`evidence/attestations` paths belong to an independent Git object tree, not a
workspace directory. Neither a documentation path nor a profile directory
can select current proof.

Machine output under `build/ethos/` or `build/evidence/` is generated material.
A bounded Attestation records the verifier, subject, scope and exact result;
its required supporting objects must remain retrievable for its retention
lifecycle. A human explanation belongs with the semantic subject it explains,
not in a duplicate proof directory.

Committed historical Claims and Chronicles remain retrievable through Git;
see [History](../history/README.md). Their old state labels are dated
observations, not current readiness. Still-valid requirements belong to their
current specification, design or execution owner. Removing historical copies
from a checkout does not resolve an unfinished requirement or authorize
resource deletion.

## Optional Semantic Assurance

Digest-only propositions remain portable and require no provider, account,
daemon, credential, network, or dedicated local account. When semantic
assurance is required, one candidate-external Attestation binds the compiled
Commitment identity, evidence digest, semantic scope, exact HEAD, verifier,
validity interval, and non-authorizing verdict. Missing, malformed, stale,
repository-local, or mismatched assurance fails closed. This is a bounded
verifier statement, not cryptographic proof of independent semantic
correctness.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
