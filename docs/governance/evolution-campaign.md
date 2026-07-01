---
subject: ethos:evolution
role: workflow
state: canonical
relations:
  canonical_for: repository governance
---

# Evolution Campaign

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

`ethos campaign hypotheses --json` exposes active hypotheses as first-class
objects. A hypothesis should be challenged, proven, canonized, or retired; it
must not linger as implicit roadmap text.

`ethos campaign closeout --json` exposes the local campaign closeout package. It
is a read-only aggregation of Work Lane closeout support, publication readiness,
release policy, unresolved parity packages, and shadow parity execution plans.
Remote publication remains deferred until an adapter is available; local
campaign closeout still proceeds through the configured candidate branch and a
local fast-forward of the accepted root.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
