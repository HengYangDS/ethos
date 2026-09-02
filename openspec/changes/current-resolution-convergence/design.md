## Context

See `proposal.md`. `CurrentResolution` already combines current authority,
official OpenSpec governance, compiled Commitment, selected scope, ordered gaps,
and one recovery action. Archive bypasses that owner in two places:
`_archive_readiness()` invokes governance again, and `compile_archive_plan()`
reloads Commitment after the official archive has changed the worktree.

Interrupted archive finalization adds one constraint: the worktree may already
contain the staged archive post-image while the exact source HEAD still holds
the active Change. The source intent must remain recoverable without treating
the changed worktree or the archive directory as a new authority.

## Goals / Non-Goals

**Goals:**

- Select archive authority and intent exactly once per non-recognition
  invocation.
- Reuse one Commitment for readiness and `TransitionPlan` compilation.
- Recover staged archive intent from the exact source HEAD through the existing
  resolver.
- Preserve native archive CAS, compensation, durable-effect recognition, and
  post-observation checks.

**Non-Goals:**

- No new resolver, DTO, registry, tracked carrier, compatibility path, or
  recovery database.
- No redesign of the common Git-effect executor.
- No proof-planner or accepted-closeout migration in this bounded Change; each
  remains an independently testable successor under the same terminal-plan
  batch.
- No adopter or remote mutation.

## Decisions

### Extend `CurrentResolution`; do not wrap it

Archive obtains the existing workspace observation and authority, then invokes
`resolve_current_resolution()` once for the requested Change. Normal archive
uses the active working-tree projection. An exact staged post-image selects a
committed-source mode whose intent is compiled from the unchanged source HEAD.
This is one mode of the same resolver, not an archive-specific authority type.

Alternative rejected: keep `_archive_readiness()` and
`load_profile_commitment()` as independent readers and compare their outputs.
Equality checks would detect some races while retaining three semantic owners.

### Pass the resolved Commitment into the effect compiler

`compile_archive_plan()` accepts the already selected Commitment. It continues
to derive the archive post-image, changed paths, tree, policy, and exact ref
update from effect-local facts. This separates immutable intent selection from
post-mutation effect observation.

Alternative rejected: recover Commitment by scanning the new archive path.
That would make archive layout an active database and repeat the retired
long-lived carrier model.

### Keep post-observation after CAS

`complete_archive()` still re-observes OpenSpec after the common Git effect and
fails into explicit committed residue if the terminal postcondition is not
met. Re-observation verifies effect outcome; it does not feed a different
Commitment back into the already closed plan.

## Risks / Trade-offs

- **Risk: staged recovery can use the mutable post-image as intent.** → Compile
  Commitment only from the exact source HEAD and validate the staged move with
  the existing archive post-image observer.
- **Risk: operation checks disappear into the general resolver.** → Keep
  archive-specific role, expected-HEAD, proof, cleanliness, collision, CAS, and
  compensation checks in their existing native owners.
- **Risk: the Change grows into all remaining consumers.** → Close archive
  convergence here; migrate proof fallback and accepted closeout in bounded
  successors after this atom is proven and retired.

## Migration Plan

1. Add regressions that fail if archive rereads governance or Commitment.
2. Add exact-source-tree selection to `CurrentResolution` for staged archive
   recovery.
3. Route archive readiness and plan compilation through one resolution and
   delete the duplicate imports and helpers.
4. Run focused lifecycle and current-resolution tests, reference closure,
   strict OpenSpec validation, repository-selected gates, exact-HEAD proof, and
   the normal archive and promotion sequence.
