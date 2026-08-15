---
subject: ethos:independent-verification-adoption
role: policy
state: canonical
relations:
  canonical_for: optional independent proof re-execution adoption
---

# Optional Independent Verification Adoption

Status: canonical.

Purpose: define the optional boundary for re-executing proof under an
independent trust identity.

See also: [Adoption Profiles](../architecture/adoption-profiles.md).

ETHOS remains local-first by default. An adopter may require an independent
verifier, but that verifier is a separately configured adapter and does not
change repository command semantics.

The adopter first binds its repository and runs the current proof contract:

```bash
ethos adopt --root <repo> --json
ethos prove --root <repo> --full --json
```

Independent evidence must identify the verifier, target repository, target
HEAD, exact command, result, and immutable evidence location. A local result
cannot claim hosted or independent verification, and an independent result does
not authorize mutation in another repository.
