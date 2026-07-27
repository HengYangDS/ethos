---
subject: docs:evidence
role: index
state: canonical
relations:
  canonical_for: evidence documentation
---

# Evidence Documentation

Status: canonical.

Purpose: explain curated proof summaries and the durable evidence boundary.

See also: [Documentation Root](../README.md), [Generated Artifact Topology](../architecture/generated-artifact-topology.md),
[Provenance And Attestation](../governance/provenance-and-attestation.md), and
[Decision Records](../decisions/README.md).

## Evidence boundary

This directory is a documentation entrypoint, not a second proof root. Current
durable evidence is carried only by `evidence/attestations/`. `claims`, `chronicle`, and
`parity` are immutable historical bytes with no current producer or authority.

Machine output belongs under generated homes such as `build/ethos/` or
`build/evidence/` until a bounded result is reviewed. A curated summary may live
here, but it does not replace the Attestation that binds verifier, scope, digest,
and HEAD.
