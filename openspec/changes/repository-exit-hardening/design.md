# Design

## Context

See [proposal.md](proposal.md). The review's findings are fixed at their owners: ownership and
records in `preimage.py`, configuration effects in `config_effects.py`, process observation in
`process.py` and `retirement.py`, durable writes in a store module, the exit's plan in
`exit_plan.py`, and its apply in `exit.py`.

## Goals / Non-Goals

Goals:

- The exit changes only what ETHOS owns, binds everything it will change in the digest, and either
  completes, resumes, or returns the repository to the state before it.

Non-goals:

- Reclaiming wheel packages: the plan names them as kept.
- The hosted qualification of `live_consumer_safe_uninstall`, which remains the release journey's
  named follow-up.

## Decisions

1. **One ownership owner.** `preimage.py` holds the activation keys and ETHOS's activation values,
   which move there from `activation.py`. A key is ETHOS's while it holds ETHOS's activation value.
   In worktree scope, the value is also ETHOS's while it is absent. `core.hooksPath` is ETHOS's
   while it names a current generation under `<common>/ethos/hooks` or a legacy one. The legacy
   layouts are `<gitdir>/ethos-hooks` and `<common>/ethos-hooks-<digest>`, which 1e3883d67 retired
   on 2026-08-24.
2. **Per-key record.** Install records a key only when it replaces a value that ETHOS does not
   own. A key that ETHOS already owns keeps its recorded entry, or stays unrecorded. The record is
   written only when an entry changes, so an upgrade never rewrites it, and a re-adoption replaces
   stale entries. Install also clears an earlier exit's receipt. A failed activation restores the
   previous record and receipt bytes.
3. **Durable records.** `replace_durably` in `ethos/adapters/store/durable.py` fsyncs the file and,
   on POSIX, its directory. Content-addressed storage shares its directory sync.
4. **The plan is the after state.** For each key, the preview decides what the exit does:
   - write the recorded value, while the key is still ETHOS's;
   - keep the current value, when the key is no longer ETHOS's;
   - leave the key, when it is ETHOS's but unrecorded.

   It also keeps `extensions.worktreeConfig` while a worktree needs it, and lists record entries
   for worktrees that no longer exist. The planned generation removals come from
   `retirement_plan`, using references from processes, interpreter bindings and configuration,
   without the hooks path that the exit removes. The digest covers all of it, and the apply
   removes only the planned generations.

5. **Resume.** An `applying` receipt keeps the repository in the exit. Its record stands in for a
   removed record file. A selector whose bytes differ from the receipt's blocks the exit with
   `adoption_exit_resume_conflict`. The original receipt is kept, and the apply marks it applied.
6. **Fence.** The apply takes the selection lock, then holds `BEGIN IMMEDIATE` on the state
   database, which is the transaction the Lease owner uses. A Lease therefore cannot start while
   the exit is inside the fence. A busy lock or database returns `adoption_exit_selection_busy` or
   `adoption_exit_state_busy`. The apply then:
   1. recomputes the plan and compares its digest;
   2. writes the receipt, unless it is resuming;
   3. removes the record;
   4. writes each key whose current value is still the planned one;
   5. verifies the effective hooks path of each worktree, where a Git error counts as unknown;
   6. removes each selector that still holds its planned bytes;
   7. marks the receipt applied.
      After the last step, it reclaims the planned generations.
7. **Compare and write.** `replace_config_values` accepts the expected values and refuses with
   `git_config_effect_stale` when a key differs immediately before the write. Git offers no
   compare-and-swap across invocations, so a change between that comparison and Git's own lock can
   still be lost. The postcondition then reports any later change.
8. **Compensation.** Compensation follows `_restore_failed_activation`. It attempts the
   configuration, the selectors, the record and the receipt, and collects every failure. Any
   failure returns `unknown`, with `adoption_exit_compensation_failed` naming all of them.
9. **Processes.** Process observation excludes the exit's own PID: `ps -o pid=,command=` on POSIX,
   and `ProcessId` on Windows. The owned paths include the installed runtime that a selector names
   on its second line. For the exit, Windows reads strictly: a process with no command line,
   except the kernel's PIDs 0 and 4, is unknown. Runtime retirement keeps its existing reading.
10. **The user's decision.** Without a record, `adoption_exit_preimage_unrecorded` names the exact
    `git config --unset-all core.hooksPath` command for each location, in the local or worktree
    scope. It also says to set the user's own path instead, if that is wanted.

## Risks / Trade-offs

- On Windows, a standard user usually cannot read every process's command line, so the exit fails
  closed there as `adoption_exit_runtime_use_unknown`. The exit tests therefore observe the process
  table through a controlled listing on Windows.
- The window between comparison and write in decision 7 remains. Only Git's own configuration lock
  could remove it.
