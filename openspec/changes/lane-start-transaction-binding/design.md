## Context

See `proposal.md`. The repository Commitment reader is the shared producer for
lane, planning, proof, and publication admission. It currently collapses every
strict parsing or validation error into a missing-carrier error. Fresh lane
apply performs another repository Commitment read after transaction setup, so
its observable boundary differs from dry-run and can fail after avoidable
effects.

## Goals / Non-Goals

**Goals:**

- Keep one strict current Commitment schema and one repository reader owner.
- Preserve precise failure identity through all consumers.
- Bind lane dry-run and apply to one pre-effect repository observation.
- Derive compensation reporting from observed effects and residue.

**Non-Goals:**

- Reading, defaulting, or silently migrating obsolete Commitment schemas.
- Adding a second result taxonomy, ledger, recovery engine, or adopter rule.
- Solving external proof binding, archive continuity, tag publication, or
  optional candidate topology in this atom.

## Decisions

### Return strict parser failures without absence translation

The existing reader remains the unique owner. It will reserve
`repository_commitment_missing` for a genuinely absent path and give
unreadable, unsupported-schema, semantic-validation, and identity failures
stable precise identities derived from the strict parser boundary.

A compatibility reader was rejected because it would create two live meanings
for Commitment bytes and let obsolete carriers authorize current mutation.

### Prevalidate before transaction setup

Fresh lane planning will resolve the repository root, exact tree, repository
identity, and repository Commitment before creating a ref, worktree, Lease, or
Change carrier. Apply will consume those validated coordinates rather than
re-reading through a different root after materialization.

Moving compensation earlier was rejected because compensation cannot repair an
effect that should never have begun.

### Observe residue before reporting compensation failure

The rollback owner will report cleanup failure only for a performed effect that
remains after cleanup. A failure before the first effect will preserve the
original blocker and a zero-residue observation.

A list of special-case suppressed messages was rejected; the positive model is
the effect journal already owned by the bounded lane transaction.

### Keep migration forward-only and separate

An obsolete tracked carrier requires an explicit public successor migration
with exact CAS. This atom only makes the defect precise and early; it does not
introduce dual-reading or mutate adopters.

## Risks / Trade-offs

- **Risk: downstream tests depend on the old misleading missing string.**
  → Update producer-to-consumer contracts and delete missing-only branching.
- **Risk: parser exceptions expose unstable library prose.**
  → Map at the repository reader boundary to a small closed set of ETHOS error
  identities while preserving bounded diagnostic detail.
- **Risk: dry-run facts become stale before apply.**
  → Bind apply to exact repository/tree identity and recheck those coordinates
  at the effect aperture rather than reparsing through a new root.
