## Context

The live accepted runtime at c9aad4a80 returns pass with a lane-status action
from lane status itself. The result algebra already derives done from a passing
result with no next action; it is the producer that invents a continuation.
Compact status deliberately defers foreign-path scope, while lane status has
already read those facts. Those two evidence depths must not share an
unconditional observation fallback.

## Goals / Non-Goals

Terminate completed reads while preserving actionable work and blocked or
unknown results. Keep foreign lanes visible without granting authority or
requiring a new task. Do not store progress, compare command strings to detect
loops, or claim that reader completion means product completion.

## Decisions

### Select by facts and observation depth

The workspace stage owner selects only an existing authoring or integration
boundary. Compact status may route to coordination detail when foreign or
unbound lanes exist and no stronger action was selected. Detailed lane status
has no repeat-observation fallback. Both readers reuse the existing exact
accepted-closeout derivation for a pending candidate.

### One meaning across entry projections

README describes official OpenSpec intent, transient Commitment and durable
Attestation without a second persistence model. Adoption examples describe the
actual profile plus official config, not a one-file or crash-atomic scaffold.
Skills and quickstart explain done as completion of the requested observation,
not repository-wide success; examples are selectable actions, not a mandatory
pipeline. Whole-system research and quality gaps remain in the existing plan.

## Risks / Trade-offs

An empty action must not hide an actual accepted transition. Test pending
candidate and stale work base independently. Coordination advisories remain
visible, but they cannot force periodic observation or authorize foreign work.
No universal independent-verifier or resource-lifecycle guarantee is added.

## Migration Plan

Remove the unconditional fallback, reuse existing closeout derivation, align
entry projections and retain exact foreign-lane safety. No persisted state
changes or adopter migration are required.

## Validation Strategy

Observe the existing public loop before changes. Use real repository fixtures
for an idle accepted checkout with and without a foreign lane; compact status
expands detail once and detailed status is done. Compare pending-candidate
actions from both readers and preserve stale-base and blocked cases. Verify
schemas, affected tests, budget, docs/skills and current full proof before
acceptance. A test that checks only equality between two wrong projections is
insufficient; assert the expected action and derived continuation.
