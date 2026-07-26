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

The kernel records Authority, Subject, Commitment, Change, Evidence,
Claim, and Chronicle facts. Governance adapters may sign those facts, publish
transparency records, or emit hosted CI artifacts. The adapter output never
replaces the repository evidence chain.

`ethos prove --json` emits an evidence set bound to HEAD and a digest. It does
not claim a release. That output remains local evidence until an adopter
promotes it into durable repository evidence or a signed release artifact.

## Optional Semantic Attestation

`digest_only` is the portable default for claims. It requires no provider,
account, daemon, credential, network, or `yheng-agent-ethos` account. It binds
only the dated evidence and declared freshness relationship; it does not assert
semantic review.

An author may use `semantic_attested` only with a typed receipt stored outside
the governed repository. The claim binds the receipt id, receipt SHA-256,
semantic-scope SHA-256, and exact HEAD; the receipt binds the claim id,
dated-evidence SHA-256, reviewer role and reference, review basis, `allow`
verdict, validity interval, canonical payload digest, and
`mints_authority = false`. ETHOS rejects a missing, malformed, stale,
repository-local, or mismatched receipt. This is a structured bounded
attestation, not a cryptographic proof of independent semantic correctness.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
