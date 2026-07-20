---
subject: ethos:assurance-program-20260712
role: plan
state: archived
relations:
  implements: DR-0006
  carrier: openspec/changes/archive/2026-07-12-assurance-program
---

# Assurance Program — 2026-07-12

Status: archived after implementation verification; final lane proof and
candidate promotion remain lifecycle work.

Purpose: describe the active change plan for optional, action-bound independent
proof re-execution.

See also: [Independent Verification Adoption](../governance/independent-verification-adoption.md),
[DR-0006](../decisions/accepted/DR-0006-proof-trust-boundary.md), and
[Archived OpenSpec Carrier](../../openspec/changes/archive/2026-07-12-assurance-program/proposal.md).

## Objective

Deliver a provider-neutral, default-disabled independent re-execution boundary
for `publish`, while preserving local-first adoption and separating a reference
OS identity from product authority.

## Design Commitments

1. Assurance vocabulary states evidence depth precisely; digest binding and
   independent re-execution do not imply semantic correctness.
2. `disabled`, `optional`, and `required` are per-action adopter policy. An
   absent policy must never require a provider.
3. A receipt binds remote, commit, tree, action, proof floor, gate policy, and
   verifier implementation. Provider keys, anchors, accounts, and paths stay
   outside governed repositories.
4. The reference adapter is one-shot, allowlisted, sandboxed, and key-isolated;
   it is a replaceable provider implementation, not an ETHOS authority.
5. External parity requires an external Git subject and adopter-owned evidence;
   generic self-shadow remains only a product regression check.

## Acceptance Sequence

1. Unit and adversarial tests cover policy modes, exact bindings, receipt-store
   confinement, trusted-anchor verification, foreign SHA, remote allowlist,
   missing sandbox, receipt publication failure, and key-free proof children.
2. Validate schemas, claims, docs, OpenSpec, lint, focused tests, and the full
   quality floor on a stable HEAD.
3. Execute head-bound proof; then refresh generic parity evidence and run the
   normal candidate/accepted lifecycle. Remote publication remains a separate,
   human-authorized action.

## Non-Goals

This program does not make a named local account mandatory, create a daemon or
schedule, claim hosted status, store private material in the repository, or
declare semantic correctness from a receipt.
