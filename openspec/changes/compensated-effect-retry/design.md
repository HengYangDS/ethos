## Context

See [proposal.md](proposal.md). The Git effect executor recognizes a plan
through the sole Attestation with its plan digest, then validates that
Attestation against current postconditions so a replayed or tampered claim
cannot pass. Work Lane start creates its ref through this executor. When a
later step fails, it deletes the ref through a second attested effect with the
opposite update and the same candidate assertion. Nothing relates the two
records, so after compensation the creation record still selects the plan
while its postcondition no longer holds. The lane-birth reader used by Change
provenance likewise counts every valid `lane.start` record for the branch.

A disposable clone of the adopter at `b9e549eb`, run with its selected runtime
`d6286a70`, reproduced the adopter's plan digests `cc524471…` and `953dd427…`.
The first failure was hook activation writing `.git/config`, not a content
mismatch. The working directory and `--root` played no part: identical retries
from `$HOME` with `--root` and from the root without it both blocked, and a new
lane name from `$HOME` with `--root` succeeded. The configuration write came
from rewriting keys whose values already matched, which `705ce5a53` already
avoids on the accepted line.

## Source Obligations

The 2026-10-12 request carries these obligations:

- Reproduce in a disposable adopter fixture, find the first failing step and
  test the outside-cwd `--root` hypothesis: accepted; resolved by the
  reproduction above.
- Stop an applied-then-compensated effect from blocking an identical fresh plan
  while preserving immutable evidence: accepted; owned by the requirement
  "Attested compensation closes its forward effect".
- Add focused regressions: accepted; tasks 1 and 2.
- Leave the adopter repository and its Attestation set untouched, follow ETHOS
  lane rules and report before publication: accepted as constraints. Proof,
  landing, installation and publication stay lifecycle obligations outside
  these tasks.
- Sandbox denial of `.git/config` writes: not an ETHOS defect by itself. The
  avoidable rewrite is handled by `705ce5a53`; that remains pending
  verification in the adopter until it selects a runtime containing the commit.

## Goals / Non-Goals

**Goals:**

- An identical plan is admissible again after an attested exact inverse.
- Lane-birth provenance ignores a compensated start.
- One inverse definition serves the executor's reverse transaction, Work Lane
  compensation and closure.

**Non-Goals:**

- Changing what Work Lane start compensates, or converging it forward.
- Treating any later effect on the same ref as closure, or deleting or
  rewriting Attestations.
- Changing recovery selection by operation and desired head. Its operations
  (candidate integration, lane refresh, archive and candidate projection) have
  no attested inverse, and its current-postcondition validation already
  rejects a compensated effect.

## Decisions

### Closure is a derived relation over immutable records

A forward Attestation is closed when another member records its exact inverse
effect digest, began observation no earlier than the forward post-observation,
and passes the existing historical validation for its own plan. Closure is
computed on read; no predicate, field or mutable index is added.

Alternatives considered: deleting or superseding the forward record would erase
evidence; a separate "compensated" Attestation would duplicate what the inverse
already proves; an attempt nonce in the plan would break idempotent recognition
of a genuinely applied effect.

### Exactness, not similarity

Only the exact inverse closes an effect: the same refs, swapped expected and
desired values and identical assertions. A raw ref update, an earlier or
invalid inverse, or a partially overlapping effect leaves the forward
Attestation selected. Closure never authorizes an effect. The identical plan is
admitted again against current refs and Lease state, and its compare-and-swap
fails if the refs moved elsewhere.

### Consumers that read live effects apply closure

Exact-plan recognition, used by the executor and by validated plan selection,
and the lane-birth boundary consume the relation from the Git effect
Attestation owner. Recovery selection is unchanged for the reason above.

### One inverse definition

The Git effect contract defines the inverse transaction. The executor's reverse
compare-and-swap and Work Lane start compensation derive from it, and the
compensation remains a separately attested `lane.start.compensate` plan.

## Risks / Trade-offs

- [Repeated compensations share one plan digest] → Pairs are ordered by
  observation time and a later forward closes an earlier inverse the same way,
  so only the newest unclosed record selects either plan.
- [Read cost] → Closure is evaluated only for records that already match a plan
  digest or a branch's lane starts. Candidates are filtered by effect digest
  before validation.
- [A forged inverse is written to the set] → It must pass historical
  validation, and closure only reopens admission against live refs; it cannot
  apply or authorize an effect.

## Migration Plan

No data migration. Existing Attestations, including the adopter's compensated
pair, are read as closed once that repository selects a runtime containing this
change. Until then, a retry succeeds only after the accepted or candidate head
moves, and a restarted lane needs explicit Change selection. Rollback reverts
the commit; no persisted state depends on it.

## Open Questions

- Whether Work Lane start should keep its attested ref and converge projections
  forward, as "Rebuildable projections converge after the authority effect"
  describes, instead of the compensation that "Work Lane start is no-clobber
  and compensation-bound" requires. Reconciling them is a separate Change.
- Whether reusing a lane name after a non-inverse effect with unchanged heads,
  such as same-day retirement and restart, needs its own supersession rule.
