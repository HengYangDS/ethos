## Context

The terminal source Change is archived and its Work Lane is retired. Its
dependency graph requires `accepted-spec-reconciliation` to start from accepted
`dev`, while current `ethos lane start` can only copy a Commitment from another
live leased Work Lane. This is a bootstrap cycle, not an authorization gap.

## Goals / Non-Goals

**Goals:**

- Start one new atomic Change from clean accepted truth without a predecessor
  Work Lane.
- Keep the new lane bound to an immutable explicit Commitment and official
  OpenSpec carrier before ordinary writes begin.
- Reconcile accepted specs to current executable behavior.

**Non-Goals:**

- Recovering or normalizing legacy leases in this Change.
- Weakening prewrite, Lease, exact-CAS, OpenSpec, proof, land, or archive gates.
- Adding a campaign manifest, compatibility reader, or generic bootstrap mode.

## Decisions

### Fresh bootstrap consumes one external Commitment

`ethos lane start` accepts an explicit repository-independent Commitment file
for a new Change when no source Work Lane is supplied. It creates a detached
candidate-based worktree, invokes the exact official OpenSpec executable to
create that Change, materializes the Commitment at the Change root, validates
both carriers, creates one deterministic initialization commit, acquires the
strict Lease, and creates the Work Lane ref through the existing exact-CAS
effect.

This is preferred over creating a source lane because the latter merely moves
the bootstrap cycle, and over deriving Commitment fields from CLI flags because
an external typed carrier keeps configuration declarative and reviewable.

### Source continuation remains exact

When `--source-root` is supplied, the existing exact live-Lease carrier copy is
retained. Fresh bootstrap and source continuation are mutually exclusive. No
archive, accepted spec, conversation, or branch name is treated as substitute
intent.

### Accepted specs are reconciled by executable ownership

Each accepted requirement must have a current source/test/schema owner. A
historical-only requirement is removed or narrowed; archived deltas remain
non-authorizing history. Validation checks grammar, while focused architecture
tests check that stale terminal behavior does not return.

## Risks / Trade-offs

- [An arbitrary file is admitted as intent] -> strict Commitment validation,
  Change identity equality, explicit path, and exact bytes/digest binding apply
  before the ref effect.
- [OpenSpec and Commitment creation partially succeeds] -> reuse the existing
  detached-carrier rollback boundary and validate before Lease/ref creation.
- [Two bootstrap modes drift] -> both compile to the same lane-start context and
  exact-CAS effect; only carrier materialization differs.
- [Spec cleanup deletes valid behavior] -> require a current implementation or
  explicit removal proof for every changed requirement.

## Migration Plan

1. Bootstrap this one successor with the same exact carrier/Lease/ref semantics
   the new public path will implement.
2. Add failing command and adapter tests for fresh bootstrap, ambiguity, invalid
   Commitment, partial failure, and source-continuation preservation.
3. Implement the minimal public path and delete the impossible
   `source_root_required` default.
4. Reconcile accepted specs, run strict OpenSpec validation and focused/full
   proof, then archive, land, and retire this short Change normally.
