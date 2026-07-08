---
subject: ethos:evolution
role: explanation
state: canonical
relations:
  canonical_for: repository governance
---

# Evolution Campaign

ETHOS governs repository evolution through one repository-truth ledger at `evolution/ledger.toml` plus campaign manifests under `evolution/campaigns/`. Documentation explains the mechanism; it does not store a parallel ledger.

ETHOS governs repository evolution through:

```text
observe -> hypothesize -> experiment -> prove -> canonize -> retire
```

Repository audit checks command-plane growth, package ontology drift, docs metadata,
schema coverage, profile leakage, and adapter boundaries. Evolution records
must either canonize a proven improvement or retire it.

Evolution uses the governed repository model. It reuses the same governance
context, command semantics, evidence contracts, and mutation discipline for
every profile.
`ethos audit` changes proof depth for the product-toolchain profile; it does
not create a private command plane or a second product lifecycle.

`ethos campaign hypotheses --json` reads `evolution/ledger.toml` and exposes active hypotheses as first-class
objects. A hypothesis should be challenged, proven, canonized, or retired; it
must not linger as implicit roadmap text.

`ethos quality evidence-freshness --json` checks the ledger as part of the
evidence freshness read model. Active hypotheses must cite resolvable proof,
review, and decision references. Proof references may be known ETHOS command
references; review and decision references are repository paths. Reviewed
non-campaign evolution entries must bind at least one evidence reference and one
decision reference, so structural evolution cannot become a second narrative
store detached from claims, chronicle, and repository truth.

`evolution/campaigns/<campaign-id>/campaign.toml` records long-running product
work as an ordered campaign manifest. A campaign is not a giant Work Lane. It
is an orchestration record whose steps name the OpenSpec change, Work Lane
branch, claim, evidence refs, and closeout state that must be completed before
later steps depend on them. Each step lands through normal Work Lane semantics:
prove, land to candidate, closeout-apply to the accepted root, then retire the
lane.

`ethos campaign status --json` exposes those manifests as the canonical campaign
read model. Planned future steps may name their intended OpenSpec changes before
the carriers exist. Active, landed, closed, or retired steps must have an active
or archived OpenSpec carrier so the campaign cannot hide ownerless work.

`ethos campaign closeout --json` exposes the local campaign closeout package. It
is a read-only aggregation of Work Lane closeout support, publication readiness,
release policy, campaign manifests, unresolved parity packages, and shadow
parity execution plans. Remote publication remains deferred until an adapter is
available; local campaign closeout still proceeds through the configured
candidate branch and a local fast-forward of the accepted root.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
