## Context

Campaign steps already carry a declared execution state, an OpenSpec change
identifier, and closeout facts.  The current validator checks ordering,
dependency retirement, non-empty closeout fields, and carrier existence in
either the active or archived home.  It does not check whether those facts tell
the same lifecycle story.  Consequently an archived, completed lane can stay
`active` indefinitely.

The historical record is sufficient to correct the current campaign: the
accepted-root reflog records the archive commit
`c17b8939f8d55082d226b3090c03a1c37cd48b37`; the candidate reflog records the
landed head `d735b62add0a0d5dc7ebdf8cb0e7e1d8deadec30`; the archived carrier
marks every task complete; and the dated hooked-write-admission Chronicle is
bound by the existing claim.

## Goals / Non-Goals

**Goals:**

- Make campaign reader output agree with carrier and closeout facts.
- Fail closed when an execution step points at an archived carrier, a terminal
  step points at an active carrier, or an execution step claims terminal
  closeout.
- Retain a truthful planned successor instead of activating a lane that has not
  been created.

**Non-Goals:**

- Do not implement the planned adopter OpenSpec scaffold step.
- Do not rewrite unrelated historical campaign records, alter foreign lanes, or
  perform remote publication.
- Do not create a second lifecycle store or a compatibility interpretation for
  contradictory state.

## Decisions

### Carrier state is inferred from the canonical OpenSpec homes

For a campaign step, `openspec/changes/<id>` denotes an active carrier and
`openspec/changes/archive/*-<id>` denotes an archived carrier.  An
`active`, `in_progress`, or `landed` step requires the former and cannot have a
`closed` or `retired` closeout.  A `closed` or `retired` step requires the
latter and a terminal closeout.  This derives lifecycle truth from existing
carrier topology rather than adding persisted flags.

### A campaign can await the next lane

The campaign remains `active` after a completed step even when every remaining
step is `planned`.  `lane_topology.next_planned_step` is the discoverable next
action; a step becomes active only when its actual carrier and Work Lane are
started.  This prevents a fabricated active lane from satisfying a display
invariant.

### Historical reconciliation records observed heads, not reconstructed proof

The corrected step records the accepted and candidate heads observed in local
reflogs, plus the existing dated Chronicle.  The new claim records the present
validator and reconciliation as historical evidence; it does not claim to
recreate remote or hosted proof.

## Risks / Trade-offs

- **Other contradictory campaign records become blocking gaps** -> this is the
  intended fail-closed behavior; reconcile each record from its own evidence.
- **Fixture campaigns omit carrier directories** -> keep the existing focused
  fixture style and assert named gaps rather than weakening production rules.
- **A campaign appears active while no lane is running** -> expose the next
  planned step explicitly; do not activate it preemptively.

## Migration Plan

1. Add regression tests for carrier/state disagreement and the truthful waiting
   state.
2. Implement the validator rules and reconcile the existing campaign manifest.
3. Update campaign documentation, bind claim and Chronicle evidence, then run
   lifecycle, claims, parity, and full proof gates.
4. Land and close out locally; defer remote publication.
