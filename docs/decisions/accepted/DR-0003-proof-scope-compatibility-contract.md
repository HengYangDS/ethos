---
subject: ethos:decision:proof-scope-compatibility-contract
role: decision
state: canonical
relations:
  canonical_for: proof scope compatibility and host-probe boundary
---

# DR-0003: Proof Scope Compatibility Contract

Status: accepted.

Purpose: record the durable ruling that external ETHOS must accept scoped proof
commands used by adopters during migration while keeping host-local probes
outside repository proof truth.

See also: [Command Plane](../../reference/command-plane.md),
[Generated Artifact Topology](DR-0001-generated-artifact-topology-contract.md),
and [Documentation Topology](DR-0002-documentation-topology-isomorphism-contract.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0003 |
| Kind | governance |
| Decision Makers | Repository owner through current migration instruction; implemented by local ETHOS Work Lane. |
| Status | accepted |
| Decision Date | 2026-07-08 |
| Decision Version | 1 |
| Decision Change Date | 2026-07-08 |
| Record Review Date | 2026-10-08 |
| Supersedes | None |
| Superseded By | None |
| Scope | `ethos prove` scoped proof compatibility and host-probe boundary for adopter migration. |
| Boundary | Owns accepted proof-scope flags and host/probe truth classification; does not make host-local readiness, hosted CI, or adopter retirement complete. |
| Context | alphasim-dmgr repository guidance invokes `pixi run ethos prove --objective ... --scope proof-kernel` and `--host --probe`. External ETHOS must not be weaker than the embedded backend during retirement migration. |
| Decision | `ethos prove` accepts known proof scopes including `proof-kernel`; unknown scopes become explicit proof gaps. `--host --probe` is accepted as optional host-readiness boundary metadata and cannot satisfy repository proof. |
| Consequences | External ETHOS can run adopter proof-kernel commands without CLI option failure, while payloads still separate repository proof, host-local probes, hosted CI, and retirement readiness. |
| Proof or Evidence | Focused CLI tests for scoped proof, host/probe boundary, and unknown-scope rejection; command-plane docs; HEAD-bound proof gates. |
| Revisit Trigger | Reopen if adopters require a stronger scope-to-gate router or if host readiness becomes a separate product gate with explicit evidence promotion. |

## Context

External ETHOS is intended to replace embedded adopter-local ETHOS without
capability loss. During alphasim-dmgr adoption, repository rules and common
commands already reference `--scope proof-kernel`, and host-readiness checks may
append `--host --probe`. A product CLI that rejects these flags cannot be the
default backend without making the adopter weaker.

## Decision

- `ethos prove --scope proof-kernel --json` is a supported compatibility
  surface.
- Scope values are explicit proof-boundary metadata. Gate selection remains
  controlled by `--gate`, `--full`, and the repository profile until a stronger
  scope-to-gate router is accepted.
- Known scopes are accepted; unknown scopes produce `unknown_proof_scope:<scope>`
  rather than silently degrading.
- `--host --probe` is accepted so existing adopter host-readiness invocations do
  not fail at CLI parsing.
- Host/probe metadata is emitted under `data.host_probe` with
  `satisfies_repository_proof=false`; it is not repository truth, hosted CI
  truth, publication proof, or embedded-backend retirement authorization.

## Consequences

Adopters can call the external product through their current proof-kernel
commands during shadow parity and rollback-window work. This narrows one
capability gap without switching defaults or retiring embedded ETHOS. Any later
implementation that maps scopes to specific gate bundles must preserve this
truth-boundary split and provide tests proving no host-local probe can satisfy a
repository proof claim by itself.

## Revisit Trigger

Revisit only when a governed adopter needs a stronger generic scope-to-gate
router, or when host readiness is promoted into a product gate with explicit
curated evidence, HEAD binding, and publication boundary rules.
