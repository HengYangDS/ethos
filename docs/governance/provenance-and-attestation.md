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

The terminal kernel persists ChangeContract and Attestation. RepositoryFacts
are freshly observed, PlanIR is transient, and historical views are derived
from Git, OpenSpec archives, and Attestations. Governance adapters may sign
Attestations, publish transparency records, or emit hosted CI artifacts, but
adapter output never replaces the repository evidence chain.

`ethos prove --json` emits a proof Attestation bound to the selected
ChangeContract digest, exact HEAD, RepositoryFacts digest, PlanIR digest, policy
digest, effect digest, and verifier boundary. It does not establish a release.
That output remains local evidence until an adopter promotes it into durable
repository evidence or a signed release artifact.

## Optional Semantic Assurance

Digest-only propositions remain portable and require no provider, account,
daemon, credential, network, or dedicated local account. When semantic
assurance is required, one candidate-external Attestation binds the selected
ChangeContract digest, evidence digest, semantic scope, exact HEAD, verifier,
validity interval, and non-authorizing verdict. Missing, malformed, stale,
repository-local, or mismatched assurance fails closed. This is a bounded
verifier statement, not cryptographic proof of independent semantic
correctness.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
