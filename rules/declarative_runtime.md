# Declarative Runtime Rules

Purpose: keep ETHOS moving toward declaration-first, functional, low-code
mechanisms instead of accumulating hand-written procedural governance code.

| Field | Rule |
| --- | --- |
| Authority | [DR-0005](../docs/decisions/accepted/DR-0005-declarative-runtime-spine.md), [Declarative Governance Compiler](../docs/architecture/declarative-governance-compiler.md), [Declarative Runtime Spine Modernization](../docs/plans/declarative-runtime-spine-modernization.md) |
| Trigger | Adding or changing public payloads, policy checks, gates, workflows, CLI commands, scaffolds, projections, read models, or graph planning logic. |
| Action | Prefer a typed contract, declaration, template, graph, or policy expression before adding imperative Python. |
| Evidence | Model/schema tests, declaration validation, parity fixture, generated surface check, focused command JSON, and HEAD-bound proof for the touched surface. |
| Stop | New hand-written Python duplicates a declaration-capable surface without an exception record and focused evidence. |

## Rules

- Public command payloads, persisted evidence envelopes, registry entries, graph
  declarations, gate declarations, and projection declarations must have typed
  contract models before they become stable surfaces.
- New governance rules and admission checks must be declaration-first. Use the
  policy declaration surface and CEL expression path when the rule is a predicate
  over typed facts. Add Python only for IO, mutation, adapter boundaries, or logic
  that cannot be safely expressed by the DSL.
- New command surfaces must be registry-first. A manual command handler may only
  bind a declared command to an adapter or preserve compatibility during a bounded
  migration.
- New scaffolds and host projections must be template-first with typed render
  context. Do not build multi-file scaffolds through ad hoc Python string
  assembly when a tracked template can express the artifact.
- New graph ordering, dependency, gate, workflow, claim, evidence, or projection
  logic must use the shared graph kernel once available. Do not add another
  bespoke topological sorter, cycle detector, or dependency walker.
- Read models must remain projections over lower-authority facts. A declaration,
  query, generated table, or rendered file does not mint repository truth.
- Heavy frameworks and hosted tools are mechanism providers only. Their state may
  become ETHOS evidence only after adapter observation, typed evidence binding,
  and claim review.
- Every exception must name the owner, boundary, why declaration is insufficient,
  the rollback path, and the proof command that keeps the exception from becoming
  hidden architecture.
