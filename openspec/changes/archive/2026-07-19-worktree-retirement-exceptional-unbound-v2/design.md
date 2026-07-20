## Context

An unbound Work Lane ref is visible repository residue, not a deletion permit.
The current public command preserves it and reports
`unbound_retire_requires_exceptional_deletion_admission`. The existing generic
lane-resolution path is intentionally scoped to linked worktrees so it can
preserve tracked and untracked deltas; it must not be widened into a ref-only
destructive fallback.

The required product behavior is therefore a separate narrow transition inside
the existing `lane retire unbound` command. It stays vendor-neutral: authority
is the accepted repository Chronicle plus current Git and lease observation, not
the caller's provider, editor, session, or host filesystem layout.

## Goals / Non-Goals

**Goals:**

- Delete only one exact accepted-ancestor `work/*` ref after a full fresh
  observation.
- Require an accepted Chronicle that names the exact branch, exact head, and
  active Claim and declares the exceptional unbound-retirement event.
- Bind the effect to a compare-and-delete Git ref update and retain no-clobber
  local attempt and receipt records.
- Reobserve status, lease, target ref, and protected refs before and after the
  effect; any drift blocks the transition.

**Non-Goals:**

- No generic unbound-ref cleanup, batch deletion, raw Git fallback, force
  worktree removal, lease deletion, or foreign-lane takeover.
- No replacement of the linked-worktree `lane resolution` preservation route.
- No Codex, provider, account, UI, remote-publication, hosted-CI, or session
  recovery coupling.

## Decisions

1. **Retain the existing command surface.** `ethos lane retire unbound` is the
   only public command changed. It remains a dry-run inspection by default and
   exposes readiness only for the narrow exceptional state.
2. **Use an accepted Chronicle as policy input.** The Chronicle path must be
   repository-local under `evidence/chronicle/`, byte-identical to the accepted
   branch version, and contain the event marker plus exact `target_branch`,
   `target_head`, and `target_claim` fields. The named active Claim must also be
   byte-identical to the accepted branch version. A current but unaccepted,
   mismatched, generic, or Claim-less record does not authorize an effect.
3. **Require all destructive controls.** Apply requires the existing explicit
   authorization plus break-glass and irreversible confirmation. A matching
   actor name never replaces those controls.
4. **Constrain observation.** Admission requires a `work/*` ref present in the
   unbound reader view, `ancestor_of_accepted`, no linked worktree, no active
   lease, a Chronicle-bound active Claim, and available protected refs. The
   exact expected head and Chronicle target head must both match the observed
   ref.
5. **Use compare-and-delete with postconditions.** The only ref effect is
   `git update-ref -d refs/heads/<branch> <expected-head>`. Protected refs are
   reobserved unchanged; the deleted ref, unbound reader entry, and active lease
   must all be absent afterwards.
6. **Keep records local and durable.** Before the effect, write a deterministic
   no-clobber attempt record. After verified postconditions, write a receipt in
   the accepted-root sibling record root. These records report the exact
   transition; they do not mint reusable authority or become repository truth
   until separately promoted.

## Risks / Trade-offs

- A stale Chronicle or moving protected ref blocks deletion rather than trying
  to repair state automatically.
- The command must preserve a ref when record writing or postcondition
  verification fails. A successful ref deletion without a receipt remains an
  explicit local residue for later reconciliation, not a completion claim.
- The accepted Chronicle check is intentionally strict and makes operators
  prepare a target-specific accepted record before they can apply the route.
