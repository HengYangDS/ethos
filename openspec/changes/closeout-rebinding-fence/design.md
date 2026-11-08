# Design

## Context

Accepted closeout renames legacy role refs in one ref transaction and then binds each worktree on a
renamed ref to its successor (`adapters/mutation/branch_roles.py`, `rename_legacy_roles` and
`bind_renamed_worktrees`). A process that stops between the two leaves worktrees whose `HEAD` names
a deleted ref. Every `land --closeout` first calls `resume_renamed_bindings`
(`application/land/operation.py`), which rewrites those `HEAD`s before any authorization or expected
head check, with an unconditional `git symbolic-ref`, and only when the invoking root's own `HEAD`
does not resolve. The design was reviewed twice as part of `catalog-root`
(`build/runtime/work/catalog-root/closeout-fence-draft.md`, reviews 1 and 2).

## Goals / Non-Goals

Goals:

- The closeout preview and `status` only read, and name each pending rebinding with a continuation.
- The apply rebinds only after its gaps pass, each worktree by compare-and-swap.
- One binder for the rename, its resumption and the retained-topic rename, behind a Git floor.

Non-Goals:

- The rename's ref transaction, Git admission of legacy role refs and the retained topic's Lease.
- Catalog entries, selection and exits, which are `catalog-root`'s.

## Decisions

1. **Detection reads only.** `pending_role_rebindings(root)` lists each worktree whose branch is a
   declared legacy role ref that no longer exists while its standard successor does, with its path,
   both refs and the successor's OID, scanning every worktree so a partial binding is found;
   `resume_renamed_bindings` retires.
2. **The preview names the gap.** With pending rebindings, `land --closeout` without `--apply`
   returns `block`, state `rebinding_pending`, one `branch_role_rebinding_pending:<ref>` gap per
   worktree and the next action `ethos land --closeout --apply --authorize --expect-head <oid>
--root <root> --json`, `<oid>` being the head the root has after the binding; `status` names the
   same gap and next action through the same detection.
3. **The apply is fenced.** With pending rebindings, the apply performs the rebinding alone, after
   `authorization_required` and `expected_head_mismatch`; it returns `branch_role_worktrees_rebound`
   and next `ethos status --root <root> --json`, and the closeout continues in the next run.
4. **Compare-and-swap per worktree.** In each worktree, one `git update-ref --stdin` transaction
   holds the successor at its detected OID and moves `HEAD` with `symref-update HEAD <successor> ref
<legacy>`, which Git applies only while `HEAD` still names the legacy ref; a changed binding
   yields `branch_role_worktree_binding_stale:<path>`, an unchanged refusal
   `branch_role_worktree_binding_refused:<path>`.
5. **A Git floor, checked first.** The rename apply, the retained-topic rename and the rebinding
   apply each probe `start`, `symref-verify HEAD <target>`, `abort` before any write and refuse
   with `branch_role_rename_git_unsupported` when Git rejects it.
6. **Previews carry no apply gap.** The rename preview no longer reports `authorization_required`,
   and the `land: --closeout` row of `_TOKENLESS_WRITES` retires, so the preview's `next` reports no
   local write.

7. **Coverage of the preview that precedes this Change.** The full proof of
   `record-retirement-preview` passed every test but measured branch coverage at 94.97 % of the
   95 % floor, its refusal and foreign-record branches untested; tests for them ride here, and the
   preview's classification reads each artifact once, which removes a branch no read could reach.

## Risks / Trade-offs

- An older Git refuses a legacy role rename instead of half-finishing it; the person upgrades Git.
  The GitLab image pins Git 2.47.3, and the hosted GitHub legs prove their runners' Git before
  `main` is published.
- The repair takes a preview and an authorized apply where the preview healed silently.
- A refused worktree leaves the others bound; each is reported, and the next preview finds the rest.
