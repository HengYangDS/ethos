---
subject: ethos:provenance
role: concept
state: canonical
relations:
  canonical_for: evidence attestation
---

# Provenance And Attestation

ETHOS evidence is designed to project into SLSA-style provenance and
Sigstore-compatible signing flows.

The kernel records Subject, Commitment, Change, Evidence, Chronicle, and
Evolution facts. Governance adapters may sign those facts, publish transparency
records, or emit hosted CI artifacts. The adapter output never replaces the
repository evidence chain.
