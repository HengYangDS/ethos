---
subject: ethos:decision:declarative-runtime-spine
role: decision
state: canonical
relations:
  canonical_for: declarative runtime spine
  informs:
    - docs/architecture/declarative-governance-compiler.md
    - docs/plans/declarative-runtime-spine-modernization.md
---

# DR-0005: Declarative Runtime Spine

Status: accepted.

Purpose: establish the durable modernization ruling that moves ETHOS away from
procedure-heavy Python surfaces toward a declaration-first governance compiler
without ceding lifecycle truth to an external runtime.

See also: [Decision Records](../README.md), [Decision Index](../decision-index.md),
[Declarative Governance Compiler](../../architecture/declarative-governance-compiler.md),
and [Declarative Runtime Spine Modernization](../../plans/declarative-runtime-spine-modernization.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0005 |
| Kind | architecture |
| Decision Makers | ETHOS maintainer and Codex work lane |
| Status | accepted |
| Decision Date | 2026-07-10 |
| Decision Version | 1 |
| Decision Change Date | 2026-07-10 |
| Record Review Date | 2026-10-10 |
| Supersedes | None |
| Superseded By | None |
| Scope | Contract models, policy evaluation, graph planning, CLI projection, scaffold generation, evidence projection, and anti-regression gates. |
| Boundary | ETHOS owns repository truth and lifecycle semantics; external frameworks provide replaceable mechanisms only. |
| Context | ETHOS has grown effective Python code around imperative policy checks, dict payload normalization, hand-written command glue, scaffold builders, and repeated graph concepts. The repository already states that `system/workflows.toml` should declare lifecycle states and that mature libraries are acceptable where they reduce total code. |
| Decision | Adopt a declarative runtime spine: Pydantic v2 as the primary contract model layer, CEL as the first policy expression DSL, an ETHOS GraphKernel backed by Python `graphlib`, Cyclopts command registry generation, Jinja2 templates for scaffolds/projections, immutable facts by default, and JSON Schema/reference validation as external contract support. |
| Consequences | New public payloads, rules, commands, scaffolds, gates, and graph plans must be declaration-first unless an explicit exception proves that a Python adapter is necessary. Heavy workflow runtimes remain adapters only. |
| Proof or Evidence | Architecture and modernization plan in this work lane; subsequent lanes must prove equivalence with focused command JSON, unit tests, `ethos report --json`, and HEAD-bound `ethos prove`. |
| Revisit Trigger | Revisit if declaration-first surfaces increase code volume, obscure authority, break command JSON compatibility, or require a long-lived external runtime to mint lifecycle truth. |

## Context

The current repository has a healthy governance kernel, but several mechanisms
are still encoded as imperative Python repetition:

- public command payloads often travel as untyped dictionaries;
- policy checks append gap strings through procedural branches;
- graph concepts appear as action graphs, gate graphs, workflow transitions,
  evidence dependencies, and projection order without a shared graph kernel;
- CLI commands repeat argument, envelope, help, JSON, and docs glue;
- adoption scaffolds and projections are built with Python control flow where
  typed templates would be smaller and easier to audit.

The modernization question is not whether ETHOS should become Pydantic, CEL,
OPA, Dagster, Temporal, Pants, or any other framework. ETHOS is a repository
trust-transition system. Its authority still comes from user instruction,
source, tests, schemas, docs, OpenSpec records, evidence, claims, rules, and
tracked repository facts. Frameworks may reduce mechanism code; they must not
become the truth center.

## Decision

ETHOS adopts the following primary spine:

1. **Pydantic v2 contract models** for public and persisted command payloads,
   evidence envelopes, command registry entries, policy declarations, graph
   declarations, and projection declarations.
2. **CEL policy expressions** for first-line guard and rule predicates over
   typed fact models.
3. **ETHOS GraphKernel plus Python `graphlib`** for deterministic graph
   validation, cycle detection, topological planning, and relation filtering.
4. **Cyclopts registry generation** so command declarations generate CLI
   surfaces, JSON envelopes, help metadata, docs tables, and smoke tests.
5. **Jinja2 tracked templates with typed contexts** for adopter scaffolds,
   evidence skeletons, docs projections, and host projection files.
6. **Immutable fact discipline**: tuples, frozensets, frozen models, and a
   persistent map abstraction for shared fact and metadata maps.
7. **JSON Schema plus reference validation** as the external contract boundary,
   generated or checked from the model spine instead of maintained as a parallel
   unchecked truth store.

The following are explicitly not the first-line ETHOS core:

- msgspec as the primary contract spine;
- attrs as the primary public model layer;
- Rego/OPA as the initial policy engine;
- CUE, Dhall, or Jsonnet as the primary ETHOS DSL;
- Dagster, Prefect, Airflow, Temporal, Pants, or Bazel as lifecycle authority;
- Typer or Click migration away from the existing Cyclopts command plane;
- a functional-programming dependency as a substitute for pure reducers and
  explicit result models.

These tools may still appear as optional adapters or future experiments when a
bounded practice claim proves net benefit without violating repository truth.

## Consequences

New work must prefer declaration-first forms:

| Concern | Preferred form | Python role |
| --- | --- | --- |
| Payload shape | Pydantic model | Validate, dump, schema-generate. |
| Rule/guard | CEL-backed rule declaration | Collect typed facts and evaluate. |
| Gate/workflow order | Graph declaration | Compile to GraphKernel and sort. |
| CLI command | Command registry entry | Generate Cyclopts binding and envelope. |
| Scaffold/projection | Jinja2 template plus typed context | Render plan and apply only when authorized. |
| Report/read model | Projection declaration | Evaluate over fact/event models. |

A Python adapter remains valid when it isolates IO, subprocess, Git, OpenSpec,
filesystem mutation, host APIs, or an algorithm that cannot be safely expressed
in the declaration surface. The adapter must still return typed results.

## Proof Or Evidence

The first proof is this decision plus the companion architecture and plan. Later
implementation lanes must add stronger evidence:

- command JSON equivalence fixtures before and after each migration;
- schema generation or schema conformance checks for every public model;
- CEL policy parity fixtures against incumbent Python checkers;
- graph digest and ordering stability tests;
- command registry generated docs/tests checks;
- scaffold dry-run and apply parity tests;
- `ethos report --json` and HEAD-bound `ethos prove` at each lane head.

## Revisit Trigger

Reopen this decision if any of the following occur:

- declaration files become less reviewable than the Python they replace;
- generated surfaces drift from tracked truth;
- external frameworks start storing lifecycle truth;
- policy evaluation cannot explain gaps in ETHOS terms;
- the effective Python code budget stops decreasing after migration lanes;
- command JSON compatibility breaks without an accepted migration record.
