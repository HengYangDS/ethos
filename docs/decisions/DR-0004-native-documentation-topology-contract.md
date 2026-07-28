---
subject: ethos:decision:native-documentation-topology-contract
role: decision
state: superseded
relations:
  historical_record_for: retired native documentation topology contract
  superseded_by: portable-docs-registry-and-ethos-repository-self-audit
  supersedes: DR-0002
  historical_carrier: ../../history/docs-topology-contract-20260708.md
---

# DR-0004: Minimal Semantic Documentation Topology Contract

Status: superseded.

Purpose: preserve the historical ruling that introduced a strict physical
documentation kernel. It is no longer a current ETHOS authority and must not
be used to impose a fixed adopter directory layout.

Current owner: [Docs Registry](../../governance/docs-registry.md) owns portable
documentation metadata, taxonomy, visible sections, command examples, and plan
discoverability. ETHOS's own repository physical shape is owned by its product
self-audit. No replacement Decision Record was created.

Historical carrier: [Documentation Topology](../../history/docs-topology-contract-20260708.md).
See also: [Decision Index](../decision-index.md),
[Decision Index](decision-index.md), and
[DR-0002](DR-0002-documentation-topology-isomorphism-contract.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0004 |
| Kind | governance |
| Decision Makers | Repository maintainers through accepted repository instruction; implemented by local ETHOS Work Lane. |
| Status | superseded |
| Decision Date | 2026-07-08 |
| Decision Version | 3 |
| Decision Change Date | 2026-07-27 |
| Record Review Date | 2026-10-08 |
| Supersedes | DR-0002 |
| Superseded By | Portable Docs Registry semantics and ETHOS repository self-audit; no replacement DR |
| Scope | The historical physical documentation topology contract used by ETHOS and selected governed repositories. |
| Boundary | Owned one strict docs kernel and rejected lifecycle state as physical topology; did not make documentation a bootstrap prerequisite. |
| Context | `docs/current/` and `docs/future/` encoded lifecycle state as directory structure, while full adoption scaffolding confused optional capability readiness with repository binding. |
| Decision | When the historical docs-topology capability was executed, require one repository-form-invariant kernel and reject `current` and `future` as roots or state values. `ethos adopt` wrote only `.ethos/profile.toml` and did not activate that capability. |
| Consequences | Product and adopter repositories could add domain roots, but no compatibility exception or alternate kernel existed. Missing docs carriers blocked only explicit docs-topology or attested transition proof, not default adoption proof. |
| Proof or Evidence | Historical focused topology tests and historical HEAD-bound proof execution. These are retained as record context, not as current commands or gates. |
| Revisit Trigger | Reopen only if a future authority establishes a stronger documentation contract that cannot be expressed by portable registry semantics and ETHOS self-audit. |

## Historical Decision

The historical strict kernel was:

- `docs/README.md` for navigation;
- `docs/decisions/` for durable rulings;
- `docs/evidence/` for curated proof summaries;
- `docs/history/` for retired rationale and archival logs;
- `docs/reference/` for stable vocabulary and references.

This was semantic isomorphism, not a product-layout clone. Product or adopter
extension roots remained domain-owned and optional. ETHOS product extensions
included `docs/architecture/`, `docs/concepts/`, `docs/governance/`,
`docs/plans/`, `docs/research/`, and `docs/start/`; they were not part of
the required kernel.

`current` and `future` were forbidden documentation roots and state values.
There was no profile compatibility policy, mapped status vocabulary, migration
exception, shim, or alternate kernel. Governed lifecycle state used explicit
metadata plus repository evidence.

Adoption bound a repository through `.ethos/profile.toml` only. The
historical docs-topology command or attested transition proof activated the
strict requirements; bootstrap did not create or claim them.

## Supersession Boundary

The historical fixed-path contract was retired because it conflated a portable
semantic registry with ETHOS's own physical product layout. The current model
keeps the reusable semantic contract portable and lets ETHOS self-audit its own
product documentation separately. Older records may cite this record as
historical context, but current design and implementation must cite the Docs
Registry and the ETHOS repository self-audit instead.

## Invariants

- Documentation metadata and discoverability remain machine-checkable.
- Adopter physical layout remains adopter-owned.
- Lifecycle state is not encoded in directory names.

## Alternatives Considered

### Strict fixed-path documentation kernel

**Pros**

- Enables simple path-set validation.

**Cons**

- Conflates portable semantics with ETHOS product layout.

**Why Rejected**

Historically selected and now superseded at the portability boundary.

### Lifecycle-shaped `current` and `future` directories

**Pros**

- Appears visually direct.

**Cons**

- Competes with Git, metadata, and evidence for state authority.

**Why Rejected**

It creates an ambiguous second state model.

### Portable Docs Registry plus ETHOS repository self-audit

**Pros**

- Preserves semantic checks while allowing subject-native physical form.

**Cons**

- Requires metadata and registry validation rather than one fixed tree.

**Why Rejected**

Not rejected; it is the current selected replacement.

## Selected Approach And Rationale

Retain this record as historical evidence and use the portable Docs Registry as
the current semantic owner. ETHOS audits its own physical form separately.

## Consequences

The fixed-path adopter requirement is retired. Current readers must use registry
semantics and must not infer current authority from this historical record.

## Proof Or Evidence

- [Docs Registry](../governance/docs-registry.md)
- Terminal-convergence portable documentation scenarios.

## Revisit Trigger

Reopen only if a real adopter requirement cannot be represented by registry
semantics without semantic loss.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 3 | 2026-07-27 | Superseded fixed-path ownership | Restore adopter portability | Docs Registry cutover |
| 4 | 2026-07-28 | Added explicit supersession alternatives | Prevent historical topology from regaining authority | Terminal-convergence decision discipline |
