---
subject: ethos:decision:proof-trust-boundary
role: decision
state: canonical
relations:
  current_owner: ../governance/provenance-and-attestation.md
---

# Proof Trust Boundary

Status: canonical rationale. Proof contracts and adapters own current behavior.

Purpose: preserve why exact local proof and independent anti-forgery assurance
are separate evidence planes rather than stronger names for the same claim.

See also: [Documentation Root](../README.md),
[Provenance And Attestation](../governance/provenance-and-attestation.md), and
[Independent Verification](../governance/independent-verification-adoption.md).

## Context

An exact local proof can bind source, policy, commands, outputs, and repository
coordinates well enough to establish local readiness. It cannot establish that
the same operating-system principal did not alter both the evidence producer
and verifier. Adding another signature or process under that same identity does
not create independence.

Conversely, requiring a hosted forge, daemon, account, credential, or network
for every proof would make local and offline repository governance impossible.
The product therefore needs an honest local baseline and an optional stronger
plane selected only when the asserted risk requires it.

## Decision

Local executed proof establishes exact local readiness. Stronger assurance
requires re-execution by an independently controlled identity and remains
optional and action-scoped. ETHOS owns the receipt contract, not operator
credentials, daemons, or provider accounts.

Every Attestation names its verifier boundary and exact bindings. A local
Attestation is never relabeled as independent, and an independent receipt does
not authorize an unrelated Git or repository effect. Missing or mismatched
independent evidence fails only the action that selected that proof plane.

## Consequences

- Local proof remains deterministic, content-addressed, and usable offline.
- Claims requiring anti-forgery assurance must select a genuinely separate
  verifier identity and retain that provenance.
- Operators own verifier deployment, credentials, and trust anchors; ETHOS owns
  only the provider-neutral request and receipt contract.
- Product status and completion reports must state which evidence plane was
  observed instead of collapsing local proof, hosted CI, and signatures into
  one generic green result.

## Rejected Alternatives

- **A MAC or signature controlled by the same local principal:** rejected as a
  false independence boundary; that principal can alter both sides.
- **Mandatory hosted verification:** rejected because it breaks local-first and
  offline operation and makes a forge an implicit authority.
- **A bundled verifier daemon and product-owned key:** rejected because ETHOS
  would own operator infrastructure and expand the trust blast radius.

## Evidence

- [Provenance And Attestation](../governance/provenance-and-attestation.md)
  defines the current Attestation and proof-plane contract.
- `src/ethos/adapters/admission/evidence/external.py` admits independently
  produced receipts without treating them as local mutation authority.
- `tests/unit/admission/test_independent_verification.py` covers exact receipt
  bindings, protected verifier configuration, and default-off behavior.
- `tests/unit/kernel/test_proof_plan_binding.py` covers local proof identity and
  exact plan bindings.

## Revisit And Retirement

Revisit when the threat model or available execution identities change, or when
a concrete verifier proves a stronger boundary with less operational burden.
Retire this record when the proof contract itself carries the distinction,
rejected alternatives, consequences, and revisit trigger without conflating a
normative contract with provider deployment guidance.
