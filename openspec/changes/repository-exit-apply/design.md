# Design

## Context

See [proposal.md](proposal.md). The archived `repository-exit` Change records the replaced
configuration at install and previews an exit; its design carries the seven review conditions of
2026-11-04. This Change delivers conditions 3, 5 and 6 and the two preview conditions that remained
open, and it refuses repositories that are not adopted.

## Goals / Non-Goals

Goals:

- A previewed exit can be applied, and it leaves the repository at its recorded configuration with
  no selector, or it leaves the repository exactly as it was.
- Status says that a repository exited.

Non-goals:

- Host supply. Consumer records stay with the host store, and `ethos hook retire-supply` finds the
  installations that the exited repository no longer selects.
- The hosted qualification of the release journey's `live_consumer_safe_uninstall`. It is a named
  follow-up for the release journey: a hosted stage must show a co-consumer kept, the exited
  repository back at its preimage, and the released installation reclaimed.

## Decisions

1. **Exact request.** An apply reuses adoption's request gaps: `authorization_required`,
   `expect_head_required` and `expect_head_mismatch`. It also needs the previewed digest, and
   reports `adoption_exit_plan_digest_required` without one or `adoption_exit_plan_digest_mismatch`
   for another. The plan covers the configuration, the record, the selectors, the Leases and the
   unlanded branches, so the digest is the compare-and-swap token for all of them.
2. **Fenced order.** Under `runtime_selection_lock`, the apply:
   1. recomputes the plan and its blockers, and compares the digest;
   2. writes the receipt;
   3. restores the recorded worktree values, then the recorded common values;
   4. verifies that no worktree's effective `core.hooksPath` resolves under `<common>/ethos/hooks`;
   5. removes `ROLLBACK`, `CURRENT` and the record, each only while it still has the planned
      bytes.
3. **Worktree configuration.** The common restoration keeps `extensions.worktreeConfig` set while
   any worktree still has worktree configuration, because Git would otherwise ignore it.
4. **Compensation.** A failure in steps 3 to 5 restores the configuration observed in step 1, the
   selector bytes and the record bytes. If compensation fails too, the result is `unknown` with
   `adoption_exit_compensation_failed`, and the receipt still names the prior state.
5. **Receipt.** `<common>/ethos/exit-receipt.json` is written atomically before the first effect.
   It holds the plan digest, each selector's bytes and hash, the configuration before and after,
   and the record. A later exit replaces it, and re-adoption is a fresh `hook install`.
6. **No record.** The exit needs a record only to restore a hooks path that ETHOS owns. While such
   a path remains, it refuses with `adoption_exit_preimage_unrecorded` and asks the user to set or
   unset `core.hooksPath`. Otherwise it removes only the selectors and changes no configuration.
7. **Not adopted.** A repository with neither selector and no hooks path that ETHOS owns is not
   adopted. The exit reports `adoption_exit_not_adopted` and plans no effect. Only ETHOS's own
   record restores configuration; files made by hand are never read.
8. **Running processes.** The preview reads running commands through the native process authority
   that runtime retirement already uses. A process that refers to `<common>/ethos/runtime` or
   `<common>/ethos/hooks` blocks the exit with `adoption_exit_runtime_in_use`, and an unreadable
   process list blocks it with `adoption_exit_runtime_use_unknown`. Configuration and interpreter
   bindings are not running processes, and reclamation still checks them.
9. **Unlanded branches.** The preview lists each topic branch, by the branch-role policy, whose head
   the accepted branch does not contain. The list informs the decision and does not block it.
10. **Reclamation.** After the selectors are gone, and still under the lock, `retire_generations`
    runs with no selection. It removes only what it can prove unused and owned, and the exit names
    every generation it keeps as residue. A deferred reclamation does not undo the exit.
11. **Status.** `hook_runtime` carries an `exit` fact while the receipt exists and no `CURRENT`
    selector does. A repository without a profile then no longer requires hooks.

## Risks / Trade-offs

- A lease that expires between the preview and the apply changes the digest, so the user previews
  again. The exit binds what the user saw rather than what is merely still compatible.
- Generations whose reclamation cannot be proven stay on disk and are named. Deleting them by name
  alone could break another Git common directory that selects them.
