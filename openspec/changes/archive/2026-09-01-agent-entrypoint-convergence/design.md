## Context

See `proposal.md` for motivation. The current product contract already owns the
semantic kernel, result envelope, OpenSpec boundary, and progressive-disclosure
requirement. The defect is projection drift: `AGENTS.md`, current documentation,
and an ETHOS-owned Change-lifecycle skill still encode a manual sequence and
duplicate OpenSpec ownership.

## Goals / Non-Goals

**Goals:**

- Make `AGENTS.md` a genuinely thin router over current repository truth.
- Make the schema-versioned result's singular continuation authoritative for
  control flow.
- Remove the duplicate Change-lifecycle skill and fixed lifecycle narration
  rather than preserving compatibility.
- Keep detailed procedure in its existing unique owners.

**Non-Goals:**

- Add a new configuration, registry, lifecycle, result field, or command.
- Change OpenSpec, Lease, role, proof, land, or publish semantics.
- Rewrite unrelated rules, skills, or historical archives.

## Decisions

### Keep one entry observation, not a fixed lifecycle

`AGENTS.md` will require one current `ethos status --json` observation and then
defer to `continuation`, `next_action`, `required_gaps`, and
`user_decision_required`. This preserves current machine semantics when the
next safe operation changes. Retaining `status -> plan -> prove -> land ->
publish` in the entrypoint was rejected because it duplicates the command-plane
reference and can be wrong for the current state.

### Link to indexes, then expand by need

The entrypoint will link only to the product contract, rule index, skill
activation registry, OpenSpec root, and documentation index. Exhaustively
listing every rule and design document was rejected because it duplicates the
indexes and defeats progressive disclosure.

### Delete the parallel lifecycle owner

OpenSpec owns Change authoring, progress, validation, and archive. ETHOS owns
admission, proof, effects, and the typed current result. The
`ethos-change-lifecycle` skill claims the boundary between them as a third
owner, so the whole package is deleted. Its handwritten multi-command driver
and the repository-governance driver are also deleted. Current command JSON and
the official OpenSpec CLI remain the only operational owners.

### Describe capabilities without prescribing a sequence

The public command roots remain capability-complete, but current documentation
must not convert their catalog into a mandatory lifecycle. The caller begins
with `status`, executes the action selected by current facts, then re-observes.
This wording replaces the fixed five-command arrows in active product,
reference, adopter, forge, and discovery surfaces.

### Preserve official planning bootstrap after partial compilation

Prewrite will derive the official incomplete-Change artifact allowance whenever
exact target paths are requested, even if the current specs already permit a
partial Commitment compilation. The allowance remains restricted to the
official artifact outputs reported by OpenSpec. Treating Commitment existence
as planning completeness was rejected because it deadlocks creation of the
remaining official artifact.

### Reuse focused owner regressions

The existing architecture suite will verify the positive entry contract:
minimal canonical links, current status observation, singular continuation,
OpenSpec ownership, and transient Commitment. The existing admission suite will
verify incomplete official artifact creation after partial compilation. This
reuses current test owners and adds no new policy engine.

## Risks / Trade-offs

- **Risk:** A shorter entrypoint provides less immediate detail. → The rule and
  skill indexes remain one link away and are loaded only when relevant.
- **Risk:** Removing helper scripts may affect users who invoked them directly.
  → They are repository skill resources, not public commands; current command
  JSON is the supported replacement and no compatibility alias is retained.

## Migration Plan

1. Update the contract delta and focused regressions.
2. Replace the entrypoint, align its direct rule/skill projections, and delete
   the duplicate Change-lifecycle skill.
3. Remove fixed lifecycle narration from active documentation and delete the
   remaining parallel driver.
4. Repair the planning-bootstrap deadlock at the current resolver owner.
5. Use current OpenSpec and ETHOS results to select every remaining transition;
   do not encode a closeout sequence in this Change.
