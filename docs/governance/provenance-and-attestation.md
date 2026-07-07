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

The kernel records Authority, Subject, Commitment, Change, Evidence,
Claim, and Chronicle facts. Governance adapters may sign those facts, publish
transparency records, or emit hosted CI artifacts. The adapter output never
replaces the repository evidence chain.

`ethos prove --json` emits an evidence set bound to HEAD and a digest. `ethos
quality provenance --json` emits the provenance envelope without claiming a
release. Both are local evidence until an adopter promotes them into durable
repository evidence or a signed release artifact.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
