---
subject: ethos:decision:generated-artifact-topology-contract
role: decision
state: canonical
relations:
  canonical_for: generated artifact topology contract decision
---

# DR-0001: Generated Artifact Topology Contract

Status: accepted.

Purpose: record the durable ruling that generated artifact placement is an ETHOS product
contract, not housekeeping, before adopter repositories retire embedded ETHOS.

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0001 |
| Kind | governance |
| Decision Makers | Repository maintainers through accepted repository instruction; implemented by local ETHOS Work Lane. |
| Status | accepted |
| Decision Date | 2026-07-07 |
| Decision Version | 2 |
| Decision Change Date | 2026-07-09 |
| Record Review Date | 2026-10-07 |
| Supersedes | None |
| Superseded By | None |
| Scope | Generated artifact topology, producer-entrypoint routing, lifecycle classes, adopter-neutral product roots, evidence promotion, proof/report placement, and adoption rollback readiness. |
| Boundary | Owns generic path policy, path router behavior, entrypoint audit behavior, audit output, proof-gate integration, and forbidden product-owned adopter roots; does not own adopter-specific directories, profiles, fixtures, or domain semantics. |
| Context | External ETHOS must become stronger than embedded adopter-local ETHOS before retirement, while keeping a small shared docs kernel across governed repositories. |
| Decision | Promote the Generated Artifact Topology Contract, producer-entrypoint routing audit, lifecycle classes, and the `docs/decisions/` Decision Record surface as ETHOS product governance. |
| Consequences | Generated proof/log/report/artifact/projection paths become auditable; `.config/` remains declarative interface; ignored tool runtime caches live under `build/runtime/tool-cache/<tool>/`, provider scratch state lives under `build/runtime/work/<provider>/`, local package artifacts live under `build/artifacts/<kind>/`; adopter-specific product roots are rejected; retired `.config/ci/scripts/` was retired as visible review debt; reusable runners now live under `tools/ci/scripts/`. |
| Proof or Evidence | `ethos quality generated-artifacts --json`, focused unit tests, architecture docs tests, docs registry checks, and HEAD-bound `ethos prove --execute --expect-head <head> --json`. |
| Revisit Trigger | Reopen only if a governed adopter cannot express its path policy through `.config/ethos/` or equivalent declarative config without product-owned adopter-specific roots. |

See also: [Generated Artifact Topology](../../architecture/generated-artifact-topology.md), [Decision Index](../decision-index.md), and [Command Plane](../../reference/command-plane.md).

## Context

ETHOS is a generic governance product. Its product repository must not accumulate
adopter-private roots such as `adopters/<adopter-id>`,
`profiles/<adopter-id>`, or `tests/fixtures/adopters/<adopter-id>`.
Adopter-specific configuration belongs in the adopting repository through
`.config/ethos/` or an equivalent declarative interface.

Development-time generated artifacts also need strong physical organization:
configuration policy, cache/runtime state, generated proof output, curated evidence,
semantic docs truth, reference docs, and durable rulings have different authority
and cleanup rules.
Without a topology contract, generated output can become a hidden authority store
and pollute closeout, proof, and retirement decisions.

## Decision

Adopt the Generated Artifact Topology Contract:

- `.config/ethos/` is declarative config, policy, and adopter interface only.
- `.cache/local-state/` and `.ethos/state/` own host-local runtime coordination state.
- `build/runtime/tool-cache/` owns ignored tool runtime caches keyed by tool name.
- `build/runtime/work/` owns provider emulator and scratch working state.
- `build/artifacts/` owns ignored local build and package artifacts.
- `build/ethos/` owns machine generated ETHOS proof, logs, reports, artifacts,
  and projections.
- `build/evidence/` owns machine generated quality/proof evidence artifacts.
- `docs/evidence/`, `evidence/chronicle/`, and `evidence/parity/` own curated
  or promoted evidence after explicit review or command promotion.
- Runtime cache, machine evidence, local artifacts, and curated evidence are
  distinct lifecycle classes: runtime cache is disposable and never promoted;
  machine evidence is generated and HEAD-bound before review; local artifacts are
  rebuildable and ignored; curated evidence is tracked and retired or superseded
  by review, not deleted as cache.
- Active producer entrypoints must route generated state before writing it:
  pytest, Ruff, import-linter, package builds, and local provider emulators must
  point to the semantic homes in this contract. Cleanup commands may remove
  residue, but they do not authorize producers that recreate root or flat homes.
- `docs/decisions/` owns durable rulings and follows the same high-level
  information architecture used by governed repositories.
- Generated drift in repo root, `.config/`, semantic docs truth roots, or source
  directories is denied.
- Root tool cache homes (`.import_linter_cache/`, `.import-linter-cache/`,
  `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.tox/`, `.nox/`,
  `.uv-cache/`) and root `dist/` are denied even when ignored.
- Retired flat generated homes (`build/cache/`, `build/runtime/gitlab-ci-local/`)
  are denied; route them through semantic subroots.
- Ignored, untracked root coverage/pytest residue is tolerated only as local
  cleanup debt so proof verdicts do not depend on whether the test gate has
  already removed `.coverage*`, `coverage.xml`, or `junit.xml`; tracked copies
  remain denied root generated drift.
- Product-owned adopter-specific roots are denied.
- The retired `.config/ci/scripts/` runners were visible review debt and must not be
  treated as the generic `.config/` model for adopters. Current reusable runners live under `tools/ci/scripts/`.

## Consequences

Future ETHOS work must route generated artifacts through the contract or update
this Decision Record with evidence. Adopter retirement cannot be justified by
narrative alone; it needs proof that external ETHOS can audit artifact placement,
keep adopter-specific state in adopter-owned declarative config, and preserve a
rollback path.

The docs organization should preserve the shared decisions, evidence,
reference, and history kernel across governed repositories. Product or domain
extension roots may exist, but they must not collapse durable rulings into
general governance prose or become mandatory truth lanes.

## Proof Or Evidence

- [Generated Artifact Topology](../../architecture/generated-artifact-topology.md)
- [Decision Index](../decision-index.md)
- `ethos quality generated-artifacts --json` (path topology plus producer-entrypoint routing)
- `uv run --group dev pytest tests/unit/governance/test_generated_artifact_topology.py tests/unit/cli/test_generated_artifact_topology_cli.py tests/architecture/test_generated_artifact_topology_docs.py -q`
- `ethos prove --execute --expect-head <head> --json`

## Revisit Trigger

Revisit only if a real adopter cannot keep adopter-specific configuration in its
own declarative interface while preserving proof, rollback, and generated output
separation.

See also

- [Decision Index](../decision-index.md)
- [Decision Dependency Map](../decision-dependency-map.md)
- [Decision Code Links](../decision-code-links.md)
