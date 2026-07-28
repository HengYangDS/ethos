# Declarative Lifecycle Rules

Purpose: keep ETHOS declaration-first, functional, and small without replacing
repository truth with framework state.

| Field | Rule |
| --- | --- |
| Authority | [DR-0005](../docs/decisions/DR-0005-declarative-lifecycle-spine.md), [Declarative Governance Compiler](../docs/architecture/declarative-governance-compiler.md), [TransitionPlan](../docs/architecture/transition-plan.md) |
| Trigger | Adding or changing contracts, facts, rules, plans, commands, effects, projections, or protocol payloads. |
| Action | Select one typed declaration or mature native mechanism before writing procedural Python. |
| Evidence | Contract/schema checks, deterministic and property tests, projection drift checks, focused command JSON, and HEAD-bound proof. |
| Stop | A new implementation duplicates an existing semantic owner or adds a wrapper without distinct meaning and measured net benefit. |

## Rules

- Persisted and external contracts use strict frozen Pydantic v2 models. Small
  transient values use frozen standard-library types; do not introduce a second
  model framework.
- Rules are predicates over typed facts. Use plain declarations first and CEL
  when an expression language is necessary. Python is reserved for fact
  collection, composition, I/O, mutation, or logic the DSL cannot express
  safely.
- Plans use `TransitionPlan`. Dependency order and cycle detection call
  `graphlib.TopologicalSorter` directly; do not introduce a graph wrapper,
  framework, or second dependency walker.
- Cyclopts declarations own CLI names, parameters, and help. Machine metadata,
  docs, schemas, tests, MCP, and SDK views derive from that owner rather than a
  parallel command registry.
- Effects are explicit, permission-bounded adapter calls with current-state and
  compare-and-swap preconditions. They return attestations; they do not publish
  hidden in-process events.
- Projections are pure reducers over lower-authority facts and attestations.
  Generated leaves are never hand-edited and must pass drift checks.
- A framework, generator, or abstraction is admitted only for a real consumer
  and only when it deletes more total maintenance than it introduces.
- Every exception names its semantic owner, boundary, why the selected mechanism
  is insufficient, deletion condition, and proof command.
