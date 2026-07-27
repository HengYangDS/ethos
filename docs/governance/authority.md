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

ETHOS product judgment starts from user instruction, repository truth, accepted
governance decisions, and fresh proof. A reader-facing North Star is derived
from this authority; it cannot override authority, evidence, or a current
decision record.

The authority fixes four irreducible anchors:

```text
Authority
Subject
Change
Attestation
```

`Commitment` collects the Subject's contracts, policies, specs, rules, promises,
and decisions. `Evidence` is material carried by an Attestation. The effective
ChangeContract owns intent, scope, acceptance propositions, and amendment
lineage; Attestations own verifier-bounded observations, judgments, proof,
effects, and historical preservation. Neither a proposition nor a historical
view is a persistent authority surface.

DocOS authority graph data under `docs/_meta/authority_graph.toml` is a typed
read model and drift gate. It records relation type, owner, canonical target,
derivation, supersession, evidence references, and stable path. It does not
create a new truth store.
