---
subject: ethos:authority
role: policy
state: canonical
relations:
  canonical_for: product judgment
  derived_views: README North Star
---

# Authority

Status: canonical.

Purpose: define the source of product judgment before reader-facing summaries,
derived views, or attested evidence.

See also: [Product Design Contract](product-design-contract.md), [Command Plane](../reference/command-plane.md),
and [Quickstart](../guides/quickstart.md).

ETHOS product judgment starts from current user instruction, repository truth,
the exact official OpenSpec projection, fresh Facts, applicable policy, and
valid Attestations. A reader-facing North Star cannot override those inputs.

The authority fixes four irreducible anchors:

```text
Authority
Subject
Change
Attestation
```

Official OpenSpec owns tracked change intent. ETHOS compiles that exact
projection into a transient Commitment with only `schema_version`, `id`, and
`acceptance`. It is not a tracked carrier, permission record, path forecast,
dependency database, or workflow state. `Evidence` is material carried by an
Attestation; Attestations durably own verifier-bounded observations, judgments,
proof, effects, and historical preservation.

Mutation authority is resolved from the compiled Commitment, applicable policy,
fresh Facts, current Attestations, a four-field Lease, and exact ref intent for
the current context. No hand-maintained graph, history scan, hook, rank,
currentness index, or reader projection owns that judgment.
