# Design

## Context

See [proposal.md](proposal.md). `_npm_roots` resolves each aggregate in topological order: a package
is resolved once every aggregate that its `via` names is resolved, and a round that resolves nothing
raises `cyclic npm aggregate references`. Its caller then requires every aggregate to reach at least
one advisory and binds each advisory to its exact locked artifacts.

## Goals / Non-Goals

**Goals:**

- A native npm report whose aggregates reach their advisories through a cycle yields the same
  advisory subjects as one without the cycle.

**Non-Goals:**

- Changing which findings block, pass or report, or how approvals and unfixed-upstream findings are
  decided.

## Decisions

- **Reachability defines an aggregate's advisories.** Each aggregate's advisories are the direct
  advisories of every aggregate reachable from it through `via`, found by a walk that visits each
  aggregate once. A cycle then needs no special case, and the result does not depend on report
  order.
- **Fail closed where nothing is reachable.** An aggregate that reaches no advisory still makes the
  caller refuse the report as `npm advisory roots unavailable`, and a reference to a missing
  aggregate is still refused as unresolved.

## Risks / Trade-offs

- [A malformed report hides an advisory-free cycle among resolvable ones] → Every aggregate must
  reach at least one advisory, so an advisory-free cycle still refuses the whole report.
