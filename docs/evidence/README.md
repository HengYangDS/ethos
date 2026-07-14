---
subject: docs:evidence
role: index
state: canonical
relations:
  canonical_for: evidence documentation
---

# Evidence Documentation

Status: canonical.

Purpose: hold curated, dated, reviewable proof summaries for ETHOS product work
and adopter migration readiness.

See also: [Documentation Root](../README.md), [Generated Artifact Topology](../architecture/generated-artifact-topology.md),
[Provenance And Attestation](../governance/provenance-and-attestation.md), and
[Decision Records](../decisions/README.md).

## Curated routes

This directory is the documentation entrypoint, not a second proof root. Use
the evidence root for the reviewed record that carries each claim:

| Need | Canonical record |
| --- | --- |
| Claim scope, verifier, digest, and carrier | [Claims](../../evidence/claims/) |
| Dated judgment and bounded observation | [Chronicle](../../evidence/chronicle/) |
| Machine-readable, HEAD-bound parity comparison | [Parity evidence](../../evidence/parity/) |
| Evidence-root layout and promotion boundary | [Evidence root](../../evidence/README.md) |
| Historical isolated overlay observation | [Claim](../../evidence/claims/real-adopter-provider-parity-evidence-20260712.toml) and [Chronicle](../../evidence/chronicle/real-adopter-provider-parity-evidence-20260712/2026-07-12.md) |
| Latest candidate-HEAD isolated adopter command-parity observation | [Claim](../../evidence/claims/current-head-real-adopter-evidence-20260714.toml) and [Chronicle](../../evidence/chronicle/current-head-real-adopter-evidence-20260714/2026-07-14.md) |
| Prior candidate-HEAD observation | [Claim](../../evidence/claims/current-head-real-adopter-evidence-20260713.toml) and [Chronicle](../../evidence/chronicle/current-head-real-adopter-evidence-20260713/2026-07-13.md) |

Machine output belongs under generated homes such as `build/ethos/` or
`build/evidence/` until it is reviewed and promoted. This lane owns promoted
human-reviewable evidence, not raw logs.
