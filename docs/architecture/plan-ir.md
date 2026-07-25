---
subject: ethos:plan-ir
role: explanation
state: canonical
relations:
  canonical_for: deterministic change planning
---

# PlanIR

PlanIR is the transient, deterministic plan compiled from repository declarations
and current facts. It owns no repository truth and performs no mutation.

Each node is one of three kinds:

- `check`: observe or verify without mutation;
- `decision`: apply declared policy to facts and prior results;
- `effect`: describe an operation that still requires current admission before execution.

Nodes declare only identity, kind, operation, and dependencies. The plan exposes
one closed aggregate verdict, `pass | block | unknown`; node observations and
judgments still belong to attestations. Permissions belong to admission, while
evidence and artifacts belong to attestations. PlanIR does not duplicate those
owners. Any structural or compilation gap forces `block`; `unknown` is reserved
for a structurally valid plan whose required proposition cannot yet be proved.

Python's `graphlib.TopologicalSorter` is the sole ordering and cycle-detection
mechanism. Missing dependencies, duplicate node identities, and cycles block the
plan. No graph wrapper, alternate graph model, or durable plan database exists.

Status: canonical.

Purpose: define the transient planning algebra without creating another truth
store or lifecycle owner.

See also: [Terminal Governance Product Design](../plans/terminal-governance-product-design.md),
[Runner And Mutation Boundary](runner-and-mutation.md), and
[Command Plane](../reference/command-plane.md).
