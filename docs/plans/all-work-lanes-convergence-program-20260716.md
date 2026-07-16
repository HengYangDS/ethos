# All Work Lanes Convergence Program — 2026-07-16

- Status: active local convergence program
- Carrier: `work/all-lanes-convergence-20260716`
- Accepted baseline: `dev@ecd9c0214738cd1db3439a0a81de334c8f378b3a`
- Candidate baseline: `candidate/dev@ecd9c0214738cd1db3439a0a81de334c8f378b3a`

## Objective

Converge the exact 60 legacy `work/*` refs observed by the 2026-07-16 audit.
For each ref, either promote its still-valid intent into accepted repository
truth or prove that later accepted work superseded it, preserve every dirty or
owner-uncertain delta before irreversible action, and then close the exact
cohort through governed local Work Lane lifecycle commands.

This is a local closeout program. It does not publish or push any remote ref.
It also does not create reusable authority over a future `work/*` ref. The
current-session user instruction authorizes investigation and completion of the
frozen cohort; every effect still binds an exact branch, HEAD, worktree
observation, lease/incarnation evidence, and accepted Chronicle judgment.

## Initial facts and truth boundary

The tracked inventory at
`evidence/chronicle/all-work-lanes-convergence-20260716/lane-inventory.json`
records a read-only Git/worktree/lease snapshot. Its initial observation found:

- 61 live `work/*` refs: 60 legacy targets plus this governance carrier;
- 57 linked Work Lane worktrees and 4 unbound refs;
- 4 valid normalized leases, including this carrier, and 53 missing leases;
- 12 dirty legacy linked lanes; the carrier becomes dirty only because it is
  writing this admitted governance record;
- 36 graph-level closeout candidates, of which 7 still have dirty worktree
  overlays and therefore are not direct retirement candidates;
- 24 graph-level implementation refs in 11 semantic families; and
- one additional post-audit dirty implementation overlay on
  `work/hosted-observation-targets-20260716`.

The inventory does not mint authority. HEAD, dirty state, lease generation,
process activity, target-observation digest, and accepted-HEAD relation are
mutable facts and must be recomputed immediately before each handoff,
preservation, integration, or retirement effect.

## Authority and coordination rules

1. Valid foreign leases remain observe-only until the holder has stopped
   writing and a normal holder-bound closeout or explicit handoff succeeds.
2. Missing, ambiguous, or owner-unknown leases are not normalized by invention.
   Exceptional action requires this Chronicle to be accepted first, followed by
   a fresh two-phase `resolution decide` and `resolution apply` observation.
3. Dirty lanes default to preservation. Plain retirement is forbidden.
4. A diverged unbound ref is preserved and integrated before unbound
   retirement; the three unbound accepted ancestors may be retired only after
   exact-head recheck.
5. Existing recovery packages and receipts are durable evidence. This program
   never clears them.
6. No `git stash`, raw protected-ref move, force push, or wildcard cleanup is
   permitted.
7. Candidate integration, accepted-root closeout, Work Lane retirement, and
   remote publication remain distinct state transitions.

## Semantic disposition model

- **Accepted ancestor/equal, clean:** take an exact observation, obtain an
  accepted judgment where ownership is missing, then use governed retirement.
- **Accepted ancestor/equal, dirty:** preserve and compare the overlay, integrate
  useful intent, then retire.
- **Superseded, clean:** demonstrate accepted absorption at exact paths, then use
  governed superseded or unbound retirement.
- **Superseded, dirty:** preserve first, then demonstrate absorption or integrate
  the remaining delta before retirement.
- **Valid direct implementation:** integrate test-first against the current
  candidate, prove, land, close accepted truth, then retire.
- **Semantic replay required:** extract requirements and tests, reimplement on
  the current candidate, and never wholesale merge stale lineage.
- **Active valid lease:** use holder-bound completion or explicit handoff after
  quiescence.
- **Missing lease:** consume an accepted Chronicle through two-phase exceptional
  resolution.
- **Diverged unbound ref:** preserve and integrate before deletion; block if the
  product cannot produce a recoverable effect.

## Executable implementation families

- **OpenSpec lifecycle and scope (5 refs):** reconcile archive transition,
  active-task, new-capability, and recovery behavior on current contracts.
- **Container contract (2 refs):** use the 2026-07-15 provider-neutral recovery
  as the sole lineage, then apply source-budget compression.
- **Candidate and lane integrity (3 refs):** reconcile generation lease, lane
  ledger, proof isolation, retirement, and closeout invariants.
- **Publication topology (2 refs):** preserve distinct publication and release
  topology surfaces; do not choose one branch wholesale.
- **Runtime evidence bundle (1 ref):** decompose the accumulated branch into
  runtime evidence, freshness, release, and quality slices.
- **Verification runtime (2 refs):** keep broker/execution-seat and wheel/sdist
  runtime boundaries distinct, then integrate receipts.
- **Quality and artifact policy (3 refs):** apply the quality-law contract first,
  then hot-path and zero-exception migration behavior.
- **Hosted runtime and supply (2 graph refs plus one dirty overlay):** reconcile
  Python bootstrap, deterministic Node/npm supply, and explicit hosted targets.
- **Governance foundations (2 refs):** replay principal delegation and staged
  secret admission as separate security boundaries.
- **Documentation navigation (1 ref):** rebuild semantic navigation coverage over
  the current documentation tree.
- **Expert remediation (1 ref):** consume the descendant implementation only
  after holder-bound closeout or handoff.

The exact branches, current heads, dirty digests, family memberships, and
planned dispositions live in the tracked inventory rather than this summary.

## Implementation discipline

- Every behavior change follows red-green-refactor. Existing lane tests are
  extracted or replayed before source; they must fail for the intended missing
  behavior on the current candidate-derived carrier before implementation.
- Each family receives a semantic requirements audit, focused proof, and an
  independent task review before it is marked complete.
- Scope is expanded by exact material paths before writes; the OpenSpec carrier
  is not a blanket exemption.
- The carrier is committed in bounded checkpoints. After parity-relevant source
  changes, generic shadow parity is refreshed and committed in this lane.
- Executed proof is HEAD-bound. Any HEAD movement invalidates prior proof.

## Local closeout definition

The program is locally complete only when fresh evidence proves all of the
following for the frozen cohort:

1. every valid intent is accepted or explicitly superseded with semantic
   evidence;
2. all dirty/owner-uncertain content has a verified preservation or accepted
   integration outcome;
3. the active carrier is complete and archived before proof;
4. the final carrier HEAD has passing strict OpenSpec, plan, parity, required
   quality gates, and HEAD-bound executed proof;
5. candidate and accepted roots converge through sanctioned ETHOS commands;
6. every exact legacy branch/worktree/lease is retired or explicitly blocked by
   a recorded product limitation, never silently deleted;
7. the governance carrier itself is retired after accepted closeout;
8. existing recovery packages remain discoverable and untouched; and
9. remote publication remains explicitly `not_performed`/deferred.

A new `work/*` ref created after the frozen snapshot is outside this authority
and must be reported separately rather than silently absorbed.
