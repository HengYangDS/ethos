## Context

See [proposal.md](proposal.md). Bounded-attestation-set gave every member one lifetime and removed
superseded heads, expired windows and repair lineage on 2026-10-16; owners then moved eleven
members into custody. A fresh process read the selected set in 16.5 s before removal and in 2.7 s
afterwards. The remaining members on 2026-10-16 at 22:54 split as follows:

| Lifetime                 | Members | Size      | Who can end them                                            |
| ------------------------ | ------- | --------- | ----------------------------------------------------------- |
| Open predicate           | 297     | 178.2 MiB | their verifiers or reviewed owners, by release (24 > 1 MiB) |
| Operation (lane records) | 1,042   | 7.3 MiB   | nothing yet; readers select retired lanes' records          |
| Head and lineage         | 32      | 0.9 MiB   | existing lifetimes                                          |

Proof admission resolves the archived intent of an admitted head through the archive and refresh
records of the lane that archived it, and proposal retirement resolves refresh provenance through a
retired lane's records. Bounded-attestation-set therefore kept every lane record.

## Goals / Non-Goals

**Goals:**

- A fresh process reads the selected set in under 2 s, so the in-process member reuse can go.
- Every remaining member has a product reader that selects it or an owner that keeps it.
- Every set writer reports its gaps and leaves no unbound custody bytes.

**Non-Goals:**

- Changing the custody store, the member size bound or the existing lifetimes of heads, windows
  and lineages.
- Deciding for a custody owner whether its evidence is still needed.

## Decisions

### Owners decide; ETHOS executes byte-exact

Custody members end only by release. A migrating owner records a bounded successor that binds the
same files as custody evidence, verifies every embedded digest against the stored bytes and then
releases the original. ETHOS never releases foreign evidence on its own judgment.

### A retired lane's records end with their last reader

The lifetime owner gains positive evidence for each reader of a retired lane's records. Proof
admission no longer needs archived intent once no selected head admits a Change archived through
that lane, and proposal retirement no longer needs refresh provenance once no proposal ref remains
that it would retire. Absence of a branch alone stays insufficient, and an unobservable reader
keeps the records.

Alternative considered: copy the needed intent into each proof record. That duplicates Commitment
content in every proof and still leaves old proofs carrying it.

### The set writer owns its gaps and its custody

A reported gap never needs caller action. An unobservable lifetime fact keeps every member, and
the next update observes again. A custody cleanup failure leaves unbound bytes, and every later
swap under the custody lock deletes all stored bytes that the new set does not bind, so the store
converges without a separate sweep. Callers that already return the writer's result, such as
`attestation record`, project its gaps; transitions that return their own result keep their shape.
Bytes an update stored under the custody lock are deleted under that lock when the update ends
without a swap and no selected member binds them. The size bound applies only to members being
added, so the record command reads the set before it refuses an input.

Alternative considered: thread both gaps through all twelve writer call sites. That changes every
transition's result for a state that needs no caller decision.

### The reuse goes once a cold read is cheap

The in-process reuse is removed in the same landing that shows a fresh-process first read below
2 s on the selected set. File-backed native output capture stays because it repairs a general
transport defect.

## Risks / Trade-offs

- [A reader selects a lane record that ended] → Each reader gets a regression, the land, closeout,
  publish, retire and proposal-retirement journeys run on a scratch copy of the real set first, and
  a missing member fails closed with the reader's existing gap.
- [Owners do not decide] → Their members stay and so does the reuse. The review on 2026-10-23 asks
  the user how to proceed with any member still undecided.

## Migration Plan

1. Obtain each owner's decision, then migrate or release its members.
2. Land lane-record lifetimes and the writer fixes after the scratch-copy journeys pass.
3. Measure a fresh-process first read and remove the reuse once it is under 2 s.

Rollback reverts the landing; removed lane records can be recorded again from a selected root that
Git has not pruned.

## Open Questions

- The exact keys by which proof admission and proposal retirement select a retired lane's records
  are recorded here by task 2.1 before the lifetime owner changes.
