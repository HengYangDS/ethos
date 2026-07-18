## Context

`work/all-lanes-convergence-implementation-20260716` preserves safety intent
that is still absent from the current `refresh_work_lane_base` implementation.
It cannot be merged as a patch: its lifecycle tests and refresh implementation
conflict with the current candidate, and the preserved lane is source-budget
blocked. The current Work Lane is therefore the sole mutation target.

The fresh cohort observation reports 79 linked foreign Work Lanes and one
diverged unbound ref. Those records are coordination facts, not an ownership
transfer. The implementation can prove current refresh behavior while the
cohort receives a separate evidence-bound disposition matrix.

## Goals / Non-Goals

**Goals:**

- Preserve the old safety invariant in the smallest current owner.
- Make every Git-mutating refresh step bind exact lane and candidate SHA facts.
- Leave a moved branch newer than the admitted SHA untouched.
- Keep the replay below the existing source budget without policy relaxation.

**Non-Goals:**

- Reproduce stale branch topology, copy old test layout, or introduce a second
  refresh implementation.
- Treat process absence, a missing lease, or the user's cohort request as
  automatic foreign-lane write authority.

## Decisions

1. **Preflight only the narrow file-backed SSH case.** If Git enables
   `commit.gpgsign`, selects `gpg.format=ssh`, and `user.signingkey` resolves to
   a file from the Work Lane root, the adjacent public key must be usable by the
   current SSH agent before replay begins. Inline, missing, and non-file values
   do not broaden the check.
2. **Replay an immutable snapshot.** Capture Work Lane and candidate SHA values,
   run the bounded signing preflight, then re-read both values. Any change
   blocks before `rebase`.
3. **Use detached replay and branch CAS.** Detach at the admitted Work Lane SHA,
   rebase onto the admitted candidate SHA, verify ancestry, and update the
   branch only with `update-ref <new> <admitted-old>`. A failed CAS reattaches to
   the live branch and reports the stale snapshot without overwriting it.
4. **Preserve bounded projection recovery.** Existing projection-only rebase
   recovery remains the resolver for a replay conflict; a non-recoverable
   failure aborts the replay and restores a normal branch checkout.
5. **Separate implementation proof from cohort closeout.** The fresh cohort
   inventory informs later exact resolution decisions. This Change does not
   make a foreign lane mutable or claim remote convergence.
6. **Keep the compact changed owners formatter-stable.** The current baseline
   already contains compact unformatted Python matrices. The three changed
   owner/test files use a local `fmt: off/on` boundary, while Ruff lint still
   runs, so deterministic format checks do not inflate a hard source budget or
   silently rewrite the established compact test carrier.

## Risks / Mitigations

- **SSH-agent state differs between GUI and terminal processes**: the helper
  checks the inherited agent and the launchd-projected socket, then blocks
  rather than starting a signing-required replay.
- **A concurrent writer advances the lane**: the CAS expectation is the exact
  admitted SHA and failure leaves the newer ref authoritative.
- **Added guards breach the source budget**: measure after each focused change
  and remove duplicated fixture or helper code only after the regression suite
  remains green.

## Migration / Rollback

The change is additive to the current owner and can be reverted as one bounded
commit before land. It does not change a foreign branch, a protected root, or
remote state. Failed refreshes remain blocked with their current branch state
intact.
