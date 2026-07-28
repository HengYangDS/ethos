---
subject: ethos:decision:proof-scope-compatibility-contract
role: decision
state: canonical
relations:
  canonical_for: proof scope compatibility and host-probe boundary
---

# DR-0003: Proof Scope Compatibility Contract

Status: accepted.

Purpose: record the durable ruling that a conforming ETHOS product must accept
scoped proof commands used by adopters during migration while keeping host-local
probes outside repository proof truth.

See also: [Command Plane](../../reference/command-plane.md),
[Generated Artifact Topology](DR-0001-generated-artifact-topology-contract.md),
and [Docs Registry](../../governance/docs-registry.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0003 |
| Kind | governance |
| Decision Makers | Repository maintainers through accepted repository instruction; implemented by local ETHOS Work Lane. |
| Status | accepted |
| Decision Date | 2026-07-08 |
| Decision Version | 2 |
| Decision Change Date | 2026-07-27 |
| Record Review Date | 2026-10-08 |
| Supersedes | None |
| Superseded By | None |
| Scope | `ethos prove` scoped proof compatibility and host-probe boundary for adopter migration. |
| Boundary | Owns accepted proof-scope flags and host/probe truth classification; does not make host-local readiness, hosted CI, or a governed transition complete. |
| Context | a reference adopter repository may invoke `ethos prove --objective ... --scope proof-kernel` and `--host --probe`. A conforming ETHOS product must not be weaker than adopter-local governance during a transition. |
| Decision | `ethos prove` accepts known proof scopes including `proof-kernel`; unknown scopes become explicit proof gaps. `--host --probe` is accepted as optional host-readiness boundary metadata and cannot satisfy repository proof. |
| Consequences | The conforming product can run adopter proof-kernel commands without CLI option failure, while payloads still separate repository proof, host-local probes, hosted CI, and execution-substrate transition judgment. |
| Proof or Evidence | Focused CLI tests for scoped proof, host/probe boundary, and unknown-scope rejection; command-plane docs; HEAD-bound proof gates. |
| Revisit Trigger | Reopen if adopters require a stronger scope-to-gate router or if host readiness becomes a separate product gate with explicit evidence promotion. |

## Context

A conforming ETHOS product may replace an incumbent adopter-local substrate
without capability loss. During adopter migration, repository rules and common
commands may already reference `--scope proof-kernel`, and host-readiness checks may
append `--host --probe`. A product CLI that rejects these flags cannot be the
selected execution substrate without making the adopter weaker.

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
  truth, publication proof, or execution-substrate transition authorization.

## Consequences

Adopters can call a conforming product through their current proof-kernel
commands during comparative assurance and recovery work. This narrows one
capability gap without authorizing a transition effect. Any later
implementation that maps scopes to specific gate bundles must preserve this
truth-boundary split and provide tests proving no host-local probe can satisfy a
repository proof claim by itself.

## Revisit Trigger

Revisit only when a governed adopter needs a stronger generic scope-to-gate
router, or when host readiness is promoted into a product gate with explicit
curated evidence, HEAD binding, and publication boundary rules.

## Invariants

- Adopter migration commands do not lose accepted inputs.
- Scope metadata does not silently become gate authority.
- Host probes cannot satisfy repository proof.
- Unknown scopes fail explicitly.

## Alternatives Considered

### Bounded scope compatibility with explicit truth boundaries

**Pros**

- Preserves migration input while preventing assurance escalation.

**Cons**

- Does not yet provide a full scope-to-gate compiler.

**Why Rejected**

Not rejected; selected below.

### Immediate scope-to-gate routing

**Pros**

- Gives callers a stronger shorthand.

**Cons**

- Creates hidden gate authority before a generic mapping is proven.

**Why Rejected**

Deferred until a stronger router has an explicit contract and evidence.

### Reject or silently coerce unknown migration flags

**Pros**

- Shrinks the parser surface.

**Cons**

- Either breaks adopters or turns errors into false proof.

**Why Rejected**

It violates explicit-gap and no-capability-loss invariants.

## Selected Approach And Rationale

Accept known scope and host-probe inputs as bounded metadata while retaining
gate and assurance authority in their existing owners.

## Proof Or Evidence

- Focused CLI scope and host-probe boundary tests.
- Exact-HEAD proof validation.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 2 | 2026-07-27 | Bound scope compatibility to explicit assurance planes | Prevent migration input from minting proof | CLI tests and command contract |
| 3 | 2026-07-28 | Added alternatives and selected rationale | Make compatibility limits durable | Terminal-convergence decision discipline |
