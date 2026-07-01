---
subject: ethos:kernel
role: concept
state: canonical
relations:
  canonical_for: kernel model
---

# Kernel Model

Status: canonical.

Purpose: define the ETHOS kernel chain that higher-level command and quality
surfaces project from.

See also: [Package Ontology](../architecture/package-ontology.md) and
[Glossary](../reference/glossary.md).

ETHOS reduces repository operation to:

```text
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

`JudgmentSource` is the authority used for product decisions. The North Star is
a derived reader view, not the judgment source. `Subject` scopes the governed
object. `Commitment` unifies contracts, specs, policies, rules, and decisions.
`Change` carries IR, transition, inscription, supersession, and current-state
movement. `Evidence` stores proof, gate, digest, and HEAD facts. `Claim` binds
evidence to a Change; digest-only claims do not prove semantic truth. `Chronicle`
keeps judged memory: what happened, which evidence was used, which decision was
made, and how current truth moved.
