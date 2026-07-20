---
subject: ethos:plans:declarative-runtime-spine-modernization
role: plan
state: canonical
relations:
  implements: docs/decisions/accepted/DR-0005-declarative-runtime-spine.md
  informs:
    - docs/architecture/declarative-governance-compiler.md
---

# Declarative Runtime Spine Modernization

Status: canonical.

Purpose: define the phased implementation plan for turning ETHOS into a more
declaration-first, functional, low-code governance compiler while preserving
repository truth and command compatibility.

See also: [DR-0005](../decisions/accepted/DR-0005-declarative-runtime-spine.md)
and [Declarative Governance Compiler](../architecture/declarative-governance-compiler.md).

## Current Pressure

The current Python surface is healthy but too procedure-heavy in the areas that
should become reusable declarations:

| Area | Pressure |
| --- | --- |
| `repository/policy` | Many imperative checkers append gap strings directly. |
| `surface/cli` | Command glue repeats parameter, handler, envelope, docs, and JSON logic. |
| `repository/adoption` | Binding generation must remain one typed declaration and one serializer leaf. |
| `repository/evidence` | Claim and evidence reports repeat shape, freshness, and projection logic. |
| graph planning | Action, gate, workflow, claim, evidence, and projection graphs lack one shared kernel. |

The plan measures success by deleted procedural Python, stable command JSON,
stronger typed contracts, and new anti-regression gates.

## Phase 0: Decision And Guardrails

Deliverables:

1. Accept the declarative runtime spine decision.
2. Publish the compiler architecture.
3. Publish this phased modernization plan.
4. Add anti-regression checks in later lanes so new work cannot silently return
   to hand-written policies, commands, multi-file generators, public dict payloads, or custom
   DAG traversal.

Evidence:

- decision record and architecture docs are linked from indexes;
- `ethos status --root <lane> --json` remains gap-free;
- docs registry and architecture checks pass when the lane is validated.

## Phase 1: Contract Spine

Admit Pydantic v2 and immutable fact discipline. Migrate the highest-leverage
public payloads first:

1. `EthosResult` and command envelope models;
2. action graph and gate models;
3. workspace status and lane coordination snapshots;
4. claim, evidence, proof, and command registry records.

Rules:

- no new public command payload may be an untyped dictionary;
- models must be strict, frozen where possible, and schema-generating;
- generated schemas must match existing command contracts or have an accepted
  migration record.

Evidence:

- command JSON equivalence fixtures;
- schema generation or validation tests;
- focused unit tests for model validation errors;
- `ethos report --json` and HEAD-bound `ethos prove`.

## Phase 2: GraphKernel Convergence

Create `ethos_core.graph` with `GraphKernel`, `GraphNode`, and `GraphEdge`, using
Python `graphlib` for deterministic topological planning and cycle detection.
Then migrate:

1. ActionGraph;
2. gate graph;
3. workflow transitions;
4. claim/evidence dependencies;
5. projection order.

Evidence:

- cycle and missing-reference tests;
- digest stability tests for action and gate graphs;
- command proof planning remains stable or has accepted migration evidence.

## Phase 3: CEL Policy Compiler

Introduce a typed policy declaration model and CEL evaluator. Start with parity
pilots before removing incumbent Python checkers.

Pilot rules:

1. protected-root mutation admission;
2. claim/evidence freshness;
3. generated artifact topology classification.

Rules:

- a new imperative checker requires an explicit exception record;
- CEL decisions must emit ETHOS gap ids, authority refs, severity, and next
  actions;
- policy fixtures must compare old and new decisions until migration closes.

Evidence:

- parity fixture matrix;
- policy declaration schema;
- `ethos audit --mode shape --json`, `ethos quality claims --json`, and
  `ethos quality evidence-freshness --json` remain stable.

## Phase 4: Command Registry Compiler

Move command surfaces to registry-first declarations. Start with the largest
surface, `ethos quality`, then expand to lane, land, report, orient, and adoption
commands.

Generated outputs:

- Cyclopts bindings;
- JSON envelope wiring;
- help metadata;
- command-plane docs table;
- command smoke tests.

Evidence:

- command JSON compatibility tests;
- docs command registry drift check;
- CLI smoke for generated commands;
- no manual command addition without a registry entry.

## Phase 5: Minimal Binding And Explicit Projections

Keep adoption at one strict repository-profile declaration serialized through
`tomli-w`. Interpret defaults instead of generating docs, skills, OpenSpec,
evidence, or provider trees. Any later projection belongs to its capability and
must prove that generation deletes more maintained code than it adds.

Evidence:

- exact one-file adoption plans;
- strict load/render round trips;
- conflict and rollback fixtures;
- generated-artifact topology checks proving no hidden scaffold remains.

## Phase 6: Evidence And Claim Event Projection

Model proof, claim, evidence, lane, and chronicle changes as typed events. Build
read models from projection declarations rather than hand-assembled dictionaries.

Targets:

1. claim registry report;
2. evidence freshness report;
3. proof run envelope;
4. chronicle promotion records;
5. report scorecard inputs.

Evidence:

- old/new report parity;
- stale evidence fixtures;
- chronicle promotion tests;
- HEAD-bound proof.

## Phase 7: Read-Model DSL

Move status, orient, report, and coordination summaries toward read-model
projection declarations over typed facts and events.

Targets:

1. `ethos orient --json` summary;
2. `ethos status --json` coordination summary;
3. `ethos report --json` advisory and next-action projections;
4. lane closeout residue summaries.

Evidence:

- command JSON fixtures;
- projection-only tests that prove read models do not mint truth;
- foreign-lane coordination fixtures.

## Phase 8: Gates As Data

Move gate registry facts to `system/gates.toml` or equivalent declaration while
keeping command execution in the imperative shell.

Evidence:

- `ethos quality gates --json` stable;
- `ethos prove --json` and selected `--execute` gates stable;
- adopter profile gate selection stable.

## Phase 9: Functional Core And Imperative Shell

Enforce architecture tests that keep pure reducers free of IO and mutation.

Forbidden in functional core:

- Git subprocesses;
- filesystem reads/writes;
- environment reads;
- current time;
- output rendering;
- repository mutation.

Evidence:

- import boundary tests;
- architecture scan for forbidden IO calls;
- focused reducer tests that use typed inputs only.

## Phase 10: Anti-Regression And Code Budget

Add quality gates that track the desired direction:

- public dict payload ban;
- imperative policy checker ban;
- manual CLI command ban;
- manual multi-file generator ban;
- custom DAG traversal ban;
- effective Python SLOC budget and trend report.

The target is not line-count minimalism by itself. The target is less
procedure, more contract, more declaration, and stronger proof.

## Work Lane Sequencing

| Batch | Lanes | Goal |
| --- | --- | --- |
| A | decision, contract spine, graph kernel | Establish reversible foundation. |
| B | CEL policy pilot, quality CLI registry, minimal binding | Delete largest process-heavy hotspots. |
| C | evidence events, read-model DSL, gates as data | Make proof/report/status declaration-first. |
| D | functional core shell, anti-regression gates | Prevent backsliding and sustain compression. |

Each lane must use the governed lifecycle: start, plan, prove, mutate, execute
focused proof, report, then land through the authorized ETHOS path.
