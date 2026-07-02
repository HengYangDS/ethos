## Context

The repository already treats OpenSpec as mandatory governance and a carrier,
not as the owner of product truth. The remaining gap is product shape: the
current system can describe ETHOS self-governance and adopter governance, but
without a shared contract a future change could drift those forms apart.

## Goals / Non-Goals

**Goals:**

- Define `self-governance` and `product-adopter` as two profiles of one ETHOS
  governance kernel.
- Make reuse explicit through a schema-validated report consumed by existing
  schema validation and proof paths.
- Keep adopter-specific and provider-specific details in profile, adapter,
  authority, strictness, and rollout bindings.
- Keep OpenSpec as a complete carrier for this change without treating it as a
  truth owner.

**Non-Goals:**

- Do not introduce a second command root for governance modes.
- Do not hardcode adopter domain terms into ETHOS core packages.
- Do not publish, push, archive remotely, or mutate another Work Lane.

## Decisions

1. **Use a governance profile report instead of a new command.**
   `ethos quality schemas`, `ethos self audit`, `ethos prove`, and
   `ethos report` already consume schema validation. Adding
   `governance_profile_report()` to that path makes the contract visible
   without expanding the public command plane.

2. **Model shared shape and allowed differences separately.**
   The shared shape contains kernel chain, trust lifecycle, capability graph,
   run steps, truth sources, and advisory projections. The allowed differences
   list is limited to authority binding, profile configuration, adapter
   binding, strictness, and rollout. This maximizes reuse while preserving the
   real operational differences between ETHOS governing itself and ETHOS
   governing an adopter.

3. **Keep OpenSpec as a carrier.**
   This change adds proposal, design, delta specs, and tasks under
   `openspec/changes/isomorphic-governance-kernel/`, but promotion remains
   bound to source, tests, schemas, docs, claims, and evidence.

## Risks / Trade-offs

- A stricter profile report can fail proof if future profile work changes one
  form without the other. Mitigation: report field-specific required gaps.
- A single report could hide adopter-specific richness. Mitigation: only the
  governing shape is shared; profile and adapter bindings remain explicit
  difference fields.
- Adding the contract to schema validation broadens local proof. Mitigation:
  the validation is in-process and uses the existing schema gate path.
