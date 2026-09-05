## Context

See proposal.md for motivation. The current spec-free compiler hashes the four
official artifacts, but also requires OpenSpec `instructions apply` to report
`all_done`. That combines two independent facts: the planning graph is complete
enough to define intent, while task checkboxes describe implementation progress.
Because product-file prewrite requires a Commitment, waiting for completed tasks
creates a circular authority dependency.

The raw digest of `tasks.md` adds a second form of the same coupling: toggling a
checkbox changes the Commitment even when every task description and acceptance
obligation is identical.

## Goals / Non-Goals

**Goals:**

- Compile spec-free intent from the complete official planning artifact graph
  before implementation starts.
- Preserve task descriptions in acceptance while excluding checkbox progress.
- Remove the OpenSpec apply-progress query from Commitment compilation.

**Non-Goals:**

- Do not relax official artifact validation or accept undeclared zero-delta
  Changes.
- Do not move task-completion checks out of proof and closeout admission.
- Do not add a new carrier, parser service, compatibility mode, or workflow
  state.

## Decisions

1. **Planning completeness, not execution completion, gates compilation.** The
   compiler continues to require official status with proposal, design, and
   tasks marked `done` and specs marked `skipped`; it no longer consumes
   `instructions apply` or requires `state=all_done`. This follows OpenSpec's
   artifact graph and keeps task progress in its existing lifecycle owner.
2. **Normalize only checkbox state in `tasks.md`.** Before hashing that official
   artifact, canonicalize leading Markdown task markers `[x]`, `[X]`, and `[ ]`
   to `[ ]`, preserving all other bytes. This binds task identity and wording
   while making progress semantically irrelevant to Commitment identity.
   Omitting `tasks.md` entirely was rejected because task descriptions carry
   implementation intent; parsing tasks into a new schema was rejected as an
   unnecessary entity.
3. **Keep fail-closed validation.** Missing artifact files, malformed official
   status, a non-skipped specs artifact, invalid digests, and undeclared empty
   deltas continue to reject compilation.

## Risks / Trade-offs

- **Over-normalization could erase task meaning** → normalize only the checkbox
  token at the start of Markdown task-list lines and hash every other byte.
- **Removing apply-state input could weaken closeout** → leave task-completion
  enforcement in existing OpenSpec lifecycle, proof, and archive owners; test
  those boundaries separately from Commitment identity.
- **Callers could retain dead apply plumbing** → delete the parameter and
  OpenSpec command invocation, then close all repository references.

## Migration Plan

Add RED tests for pre-implementation compilation and checkbox-invariant digest,
remove the apply-progress dependency from the single compiler owner, update
focused callers/tests, and run current resolution plus prewrite regressions.
Rollback is the exact parent commit; no persisted migration is required because
Commitment is transient.
