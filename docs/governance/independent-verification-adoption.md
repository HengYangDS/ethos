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

## Provider And Receipt Admission

The independent provider is an operator-deployed capability outside repository
write authority. Its configuration, trust anchor and receipt store remain
protected from the invoking identity. Public configuration must be readable by
the verifier; signing secrets are not stored or exposed in that inventory.
The current adapter owns configuration discovery and signature verification.

Required verification first checks that provider configuration is available,
protected, readable and valid. Missing or unreadable configuration requests
operator repair before asking for a receipt. Disabled policy and optional policy
without a selected receipt retain local-first behavior. A selected optional
receipt is still checked and cannot turn malformed evidence into success.

The provider emits a receipt matching
[the existing contract](../../system/schemas/kernel/independent-verification-receipt.schema.json)
in its own protected store. It binds the exact repository, commit, tree, action,
proof floor, policy, implementation and issuer. Signature and validity are
checked separately. For control replacement, the proof-floor digest binds the
full subject, including trusted predecessor, proposed controls and proof.

A missing or invalid receipt requests a valid signed result from that provider;
ETHOS does not invent a filename inside Git-private state or prescribe an
unavailable broker command. Closeout accepts the actual returned path through
`--independent-verification-receipt`; publication uses
`ETHOS_INDEPENDENT_VERIFICATION_RECEIPT`. Read-only status, proof, package tests
and local signatures do not create that receipt. Reobserve exact admission after
the operator supplies it; only a passing current decision permits the effect.
