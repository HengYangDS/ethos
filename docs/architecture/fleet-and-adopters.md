---
subject: ethos:fleet-adopters
role: explanation
state: canonical
relations:
  canonical_for: external repository governance
---

# Adopters

Status: canonical.

Purpose: define how ETHOS governs one external repository without creating a
second command plane or a central adopter task store.

See also: [Adoption Profiles](adoption-profiles.md) and
[Repository Profile Contract](../governance/repository-profile-contract.md).

ETHOS governs a repository through one explicit binding and its declared
profile. Profiles choose repository facts, adapters, and proof depth; they do
not change the public command meanings.

```bash
ethos adopt --root <repo> --json
ethos status --root <repo> --json
ethos prove --root <repo> --full --json
```

Adopter evidence remains in that repository's tracked surfaces. Provider state,
editor state, and generated projections are adapters. They must be promoted
into source, tests, schemas, docs, OpenSpec, claims, or evidence before they
support an adopter claim.
