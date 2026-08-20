## Context

See `proposal.md` for the observed failure class. The repository already has
OpenSpec 1.9, native lifecycle Attestations, exact Git effects, Lease CAS, and
archive scope projection. The defect is that these existing owners are joined
only for the ideal one-commit path. Readers and hooks then fall back to active
Change or generic Lease checks after a valid official archive or an interrupted
start commit.

## Goals / Non-Goals

**Goals:**

- Make the official OpenSpec result and the exact Git/Lease effect one
  verifiable finalization boundary.
- Reuse the existing archive binding, start-effect Attestation, Lease CAS, and
  public lifecycle commands; do not add a second recovery database or ledger.
- Recover a durable partial effect without replaying OpenSpec, creating a
  second Git commit, or guessing a holder.
- Make all reader and mutation surfaces select the same finalization scope.
- Keep lock-sensitive hook reads bounded and side-effect free.

**Non-Goals:**

- Changing OpenSpec's official schema, templates, or archive behavior.
- Automatically taking over a different holder's Lease.
- Treating an archive directory, a hook environment variable, or a historical
  path as authority without an effect Attestation.
- Solving runtime self-heal, profile migration, publication tags, or adopter
  repository changes in this Change.

## Decisions

### Reuse one lifecycle effect authority

Extend the existing archive-transition facts and start-effect Attestation
validation into one finalization selector. The selector binds repository,
source Commitment digest, previous HEAD/tree, exact staged/index tree, official
OpenSpec result, changed paths, resulting HEAD/tree, Lease generation, and
effect Attestation. A valid selector returns a state such as completion,
archive, post-archive closeout, or start recovery; it does not mint authority.

Alternative rejected: add a special `archive-finalization` hook exception or a
new recovery store. That would create a second semantic owner and would leave
the same inconsistency for Change start.

### Recover ancestry, not just the immediate parent

For an interrupted start, locate the unique committed successor whose first
parent is the Lease-bound expected HEAD and whose carrier/Attestation matches
the requested Change. Later commits are admitted only when every intervening
commit is inside the same exact Commitment scope and the final tree/index and
effect digest remain bound. Ambiguous, dirty, foreign, or drifted ancestry
blocks before mutation.

Alternative rejected: blindly rebind the Lease to current HEAD. A current HEAD
alone cannot prove which Change produced it.

### Finalization is a Lease CAS, not a new Change

Apply recovery by re-reading all coordinates, reconstructing or validating the
original effect witness, and performing one exact successor Lease CAS. The
operation is idempotent: if the successor Lease and terminal Attestation are
already present, it returns the same receipt. Missing or different-holder
states route to the existing resume/takeover authority; no implicit same-holder
assumption is made.

### Scope attribution maps projections back to the source Change

Archive directories, canonical `openspec/specs/**`, policy files, and generated
projection paths are attributed to the active source scope only when the
official archive result and exact projection receipt name and hash them. A
path not in that receipt remains uncovered. This preserves fail-closed behavior
without demanding a new active Change after archive.

### Hooks do not re-enter repository mutation

Reference-transaction and prewrite hooks consume bounded prepared-effect facts
and read-only Git observations. They must not launch maintenance, repack, or
any command that can acquire a Git ref lock while Git already holds the
transaction lock. If an observation is unavailable, the hook reports a stable
`effect_observation_unavailable` gap and the public lifecycle command supplies
the next action.

## Risks / Trade-offs

- [Risk] A later commit is incorrectly attributed to an earlier Change →
  Mitigation: require unique ancestry, exact path scope, exact source/tree
  digests, and a matching effect Attestation; otherwise fail closed.
- [Risk] Recovery is attempted after external drift → Mitigation: re-observe
  refs, worktree, index, Lease, holder, and receipts immediately before CAS.
- [Risk] Hook execution becomes slower → Mitigation: use prepared immutable
  facts and bounded read-only probes; never run full governance or maintenance
  from a Git hook.
- [Risk] Historical archive artifacts are mistaken for current authority →
  Mitigation: accept only effect-bound paths and retain archive bytes as
  historical evidence, not selectors.

## Migration Plan

1. Add RED fixtures for the two adopter reproductions and the ETHOS interrupted
   start, including exact zero-effect and lock-reentry observations.
2. Rename and modify the existing archive-effect requirement using the complete
   OpenSpec delta block; delete any duplicate archive/finalization wording.
3. Make one selector own start recovery and archive finalization; remove the
   command-specific fallback that requires active Change coverage.
4. Add exact Lease recovery and stable diagnostics for missing, expired,
   different-holder, and ownerless states.
5. Run focused tests, OpenSpec 1.9 strict validation, full proof, and archive
   through the public ETHOS command plane.

## Open Questions

None. Any unresolved authority or recovery decision would change the contract
and must not be deferred into implementation.
