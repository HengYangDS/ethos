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
and [Quickstart](../start/quickstart.md).

ETHOS product judgment starts from current user instruction, repository truth,
the selected Commitment, fresh Facts, and valid Attestations. A reader-facing
North Star is derived from this authority; it cannot override those inputs.

The authority fixes four irreducible anchors:

```text
Authority
Subject
Change
Attestation
```

`Commitment` collects the Subject's contracts, policies, specs, rules, promises,
and decisions. `Evidence` is material carried by an Attestation. A Commitment
owns immutable intent, scope, acceptance propositions, and authority references;
changed intent creates a new Commitment. Attestations own verifier-bounded
observations, judgments, proof, effects, and historical preservation. Neither a
proposition nor a historical view is a persistent authority surface.

Authority is resolved from the selected Commitment, applicable policy,
fresh Facts, and current Attestations for the exact subject and context. No
hand-maintained graph, rank, currentness index, or reader projection owns that
judgment.
