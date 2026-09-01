## Why

The tracked agent entrypoint predates the current OpenSpec-owned,
Continuation-driven ETHOS model. It still prescribes a broad manual load order
and fixed command sequence, which can make stale prose compete with current
machine facts and the singular safe next action.

## What Changes

- **BREAKING**: Replace the fixed startup checklist with a thin entry contract:
  read repository-local authority, observe current state, and follow the result's
  typed continuation and singular next action.
- Keep OpenSpec as the sole Change, design, specification, and task-progress
  carrier; treat Commitment as transient compilation and skills as optional
  procedural projections.
- Keep official Change authoring writable through its declared artifact
  sequence even when a partial Commitment can already be compiled.
- Move detailed lifecycle procedure out of `AGENTS.md`; link to its unique
  owners instead of duplicating it.
- Align the agent rule and repository-governance skill with the same startup
  semantics, and delete the ETHOS-owned Change-lifecycle skill because OpenSpec
  already owns that lifecycle.
- Remove the fixed five-command sequence from current product, command,
  adopter, forge, and discovery documentation; retain the commands as
  independently addressable capabilities selected by current facts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `assistant-projections`: The first loaded agent surface follows current typed
  continuation instead of prescribing a stale fixed workflow.

## Impact

Affected surfaces are `AGENTS.md`, `rules/agents.md`, the skill registry and
repository-governance projection, current lifecycle wording, OpenSpec bootstrap
admission, the assistant-projections contract, and focused regressions. No new
persistent state, lifecycle, command root, compatibility alias, or authority
carrier is introduced.

Out of scope: changing the semantic kernel, OpenSpec's native lifecycle,
repository roles, Lease semantics, or unrelated skills and documentation.
