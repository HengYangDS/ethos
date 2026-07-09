---
subject: ethos:declarative-governance-compiler
role: explanation
state: canonical
relations:
  canonical_for: declarative governance compiler architecture
  decided_by: docs/decisions/accepted/DR-0005-declarative-runtime-spine.md
---

# Declarative Governance Compiler

Status: canonical.

Purpose: define the target architecture that lets ETHOS become more
declaration-first, functional, low-code, and reusable while preserving repository
truth and lifecycle authority.

See also: [DR-0005](../decisions/accepted/DR-0005-declarative-runtime-spine.md),
[Workflow Runtime](workflow-runtime.md), [Action Graph](action-graph.md), and
[Declarative Runtime Spine Modernization](../plans/declarative-runtime-spine-modernization.md).

## Boundary

ETHOS is not adopting an external workflow engine as its center. The compiler
reads tracked repository declarations and lower-authority facts, then emits
plans, decisions, evidence, and projections. It does not mint truth by itself.

```text
Repository truth
  Git + source + tests + schemas + docs + OpenSpec + evidence + claims
        ↓
Typed fact collection
        ↓
Contract validation
        ↓
Policy evaluation
        ↓
Graph compilation
        ↓
Projection and command execution
        ↓
Evidence, claims, reports, and chronicle entries
```

The imperative shell owns Git, filesystem, subprocesses, clocks, network, host
providers, and mutation. The functional core owns contracts, reducers, policy
decisions, graph compilation, and projection models.

## Spine Components

| Layer | Declaration | Runtime mechanism | Output |
| --- | --- | --- | --- |
| Contracts | Pydantic models and generated/checked JSON Schema | strict validation and serialization | typed payloads and schemas |
| Facts | fact collectors plus immutable fact maps | IO adapters at shell boundary | typed fact snapshots |
| Policies | `system/policies/*.toml` with CEL predicates | CEL evaluator | decisions and gap records |
| Graphs | graph/gate/workflow declarations | ETHOS GraphKernel + `graphlib` | deterministic plans |
| Commands | `system/commands.toml` | Cyclopts registry compiler | CLI, JSON envelope, docs, smoke tests |
| Templates | tracked Jinja2 templates | typed render context | scaffold/projection plans |
| Read models | projection declarations | pure projection reducers | status, orient, report, evidence freshness |

## Functional Core Contract

Core functions should have the following shape:

```text
InputModel -> DecisionModel
Facts + PolicySet -> PolicyDecision
GraphDecl -> GraphPlan
Events + ProjectionDecl -> ReadModel
```

They should not read files, spawn subprocesses, inspect Git, consult current
time, print output, or mutate state. Those operations belong to adapters and
command surfaces.

## Declarations

The target declaration homes are:

```text
system/commands.toml
system/gates.toml
system/workflows.toml
system/policies/*.toml
system/projections/*.toml
templates/adoption/**
templates/docs/**
templates/evidence/**
```

A declaration must name its authority, expected inputs, emitted output model,
and proof surface. A declaration that changes lifecycle behavior must be backed
by OpenSpec and evidence in the same way as Python code.

## Exception Rule

Python remains appropriate when the logic is:

- IO or mutation;
- a boundary adapter for Git, OpenSpec, subprocesses, or host providers;
- an algorithmic primitive not safely expressible in the DSL;
- a compatibility bridge during migration;
- an explicitly accepted escape hatch with tests and an owner.

The exception must be narrower than the declaration it replaces. It must not
become a hidden second rule system.

## Heavy Framework Boundary

The following are not ETHOS truth centers: workflow engines, build systems,
policy servers, task ledgers, board tools, TUI apps, MCP servers, hosted CI, and
agent platforms. They may be observed or adapted only through typed evidence and
claim boundaries.

```text
External engine result -> adapter observation -> ETHOS evidence -> claim review
```

Never:

```text
External engine state = ETHOS lifecycle truth
```

## Completion Shape

The architecture is realized when new rules, commands, gates, scaffolds,
read-model fields, and graph plans are added by declaration first; Python code
only compiles, validates, evaluates, executes adapters, and projects results.
