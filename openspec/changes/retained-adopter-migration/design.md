# Design

## Context

See proposal.md for the replacement dependency. Current branch roles select `work/*`, while an
already managed adopter retains `task/*` and a dated active Change. Normal prewrite rejects
those identities. The current role-rename operation covers protected roles, not owned topics.

## Goals / Non-Goals

**Goals:**

- Reuse existing effect and observation owners to make retained resources authorable.
- Reject an unusable predecessor before installation work without rejecting valid external supply.
- Keep history, ownership and failure recovery observable through their native carriers.

**Non-Goals:**

- No alternative branch ontology, persistent migration registry or indefinite compatibility facade.
- No blanket private-runtime prohibition, cached Git authorization or weakened normal prewrite.
- No adopter activation, publication or retirement inferred from fixture acceptance.

## Decisions

### Admission stays with the existing runtime scope owner

The private marker alone does not determine sharing. A repository-private generation in another
Git-common store is inadmissible; an external installation can be valid. Installation acceptance
passes its actual destination to `require_runtime_selection_scope` before setup and rechecks the
same predicate at activation. A second resolver or a private-flag shortcut would duplicate policy.

### Retained identity migration precedes normal authoring

Use fresh native refs, committed declarations and the current holder to bind a bounded rename.
Git owns the ref transaction; worktree and Lease projections retain their existing recovery owners.
An attested ref effect is not reversed merely because a projection subsequently needs recovery.
OpenSpec owns Change artifact semantics; migrate through its existing carrier operation rather than
copy tasks into a new checklist or accept the old name permanently.

### Actual consumers determine retirement

The retained fixture exercises nonempty predecessor state and legacy authoring identities.
Upgrade, rollback and reactivation must preserve their named resources and restore authoring.
Only a separately admitted adopter cutover permits removal of its equivalent implementation.

## Risks / Trade-offs

- Ref, Lease or content drift → re-observe and reject before effect; retain precise recovery evidence.
- A retained identity collides with a current one → report the exact collision without merging intent.
- A valid installed predecessor is private-marked → evaluate physical scope, not a blanket flag.
- Fixture success is mistaken for adoption → keep source, package and adopter acceptance separate.

## Migration Plan

First repair input admission with a distinguishing regression. Then qualify and implement retained
identity transitions through existing native owners. Exercise the installed predecessor's upgrade,
rollback and renewed authoring before any separately authorized adopter cutover. Preserve required
failed receipts and recovery consumers until their owning transition releases them.
