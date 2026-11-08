# Design

## Context

`record-retirement-preview` (archived) plans store records that may retire and deletes nothing. The
archived `rc-plan` (Appendix D) designs the apply; this Change's design passed four review rounds on
2026-11-08 (`build/runtime/work/store-retention/apply-review-1.md` to `apply-review-4.md`). The
measured plan over ETHOS's own store held 1,380 items and 5,059,593,399 bytes.

## Goals / Non-Goals

Goals:

- Delete only planned items that a fresh scan still selects, recoverably at every point.
- Defer rather than race a writer: another ETHOS interpreter of the repository, a held lock or a
  moving Attestation set.

Non-Goals:

- Publication requests and superseded lane units (`record-retirement-kinds`, which also adds the
  retention of plans and receipts), custody, runtime generations, packages, hooks and tool supply.

## Decisions

1. **One deleting step.**
   `ethos hook retire-records --expect-plan <digest> --apply --authorize --json`, as `retire-supply`
   spells it; without `--expect-plan` it refuses with `record_retirement_plan_required`, without
   `--authorize` with `authorization_required`. A preview with candidates names it as `next`;
   `_DESTRUCTIVE` gains `hook retire-records: --apply --authorize --expect-plan`.
2. **Locks.** Every lock is taken without blocking, created with
   `fallback_to_soft=False, preserve_lock_file=True`: `retention.lock` for the whole preview or
   apply (`record_retirement_in_progress`), the proof slot only around artifact batches, with a
   `proof-slot.json` holder record, and the lane retirement lock around lane-unit batches. No owner
   lock covers every writer of its kind (proofs write after releasing the slot, readiness and merges
   take none); safety rests on the mtime refresh, tombstones, rechecks, the writer check and the
   custody compare. The preview's docstring stops claiming the slot keeps writers out.
3. **Recovery first.** A tombstone is `^\.[0-9a-f]{64}\.(json|zip)\.retiring$` in an owned
   directory. At the start of every preview and apply, under `retention.lock`, after the runtime
   check (so an unselected runtime never writes the store) and before any other refusal, each
   tombstone is restored by `os.link(tombstone, name)` and then unlinked; on `FileExistsError` its
   digest is checked and the tombstone unlinked, and on a digest mismatch both stay and the pair is
   reported. The roots scan skips tombstones and writers' `.<name>-*` temporaries in owned
   directories.
4. **Fresh candidates.** The apply re-runs the preview's own classification and closure, so young
   items' and reached items' tokens count, and deletes, per item, the intersection of the plan and
   the fresh candidates: same kind and file set, sizes and mtimes as planned, every path in this
   store's lstat-checked owned directories. A planned file already absent (`lstat` finds no entry; a
   symlink or non-regular file there is a change) counts as done, and a unit's state is judged
   against the plan minus the apply's own deletions, so a rerun continues a half-deleted unit. One
   predicate per kind beside `classify_store` rechecks an item at apply: the seam that
   `record-retirement-kinds` fills. Plans record store-relative paths under `schema_version` 2; a
   schema-1 plan refuses with `record_retirement_plan_mismatch`. One token set serves the whole run:
   every item that stays (restored, kept, or outside the plan and fresh candidates) lends its
   tokens, closed over as the preview's loop does.
5. **Batches.** One batch per kind: proof-check documents, then attempt archives and merge
   preimages, then all lane units in one batch, each unit whole with its receipt last. Before each
   batch the apply rechecks that it is the selected runtime and stops with
   `record_retirement_runtime_unselected` otherwise. A batch renames its files to tombstones
   (`os.replace` only over a digest-checked stale tombstone), rechecks them, runs the writer check
   and the compare, then unlinks or restores, at most 200 unlinks per custody hold. Every deferral
   names its reason (`record_retirement_batch_deferred:<kind>:<reason>`, reason `writer`, `custody`,
   `slot`, `lane-lock` or `unlink`). `PermissionError` on rename keeps the item (`in_use`); on
   unlink the item counts as deferred (`unlink`) and stays a tombstone for the next run's restore.
6. **Writer check.** After a batch's renames and before its compare, the apply reads
   `process_commands(root, exclude_pid=os.getpid(), strict=True)`
   (`adapters/repo/runtime/retirement.py:72-99`); an unknown or withheld listing defers (`writer`).
   A new reader beside the module's space-tolerant path reader (`:187-215`), normalizing Windows
   separators as `:158` does, reads the path that begins the command and, only when that is a shell
   or a Python interpreter, the path after it, resolving only their parent directory. The batch
   defers when one of them is a `python*` or `ethos` file, or on Windows `python*.exe` or
   `Scripts/ethos.exe`, under a writer root of this repository: its `runtime/` generations, the host
   installations whose consumer records name its Git common directory or whose consumers are unknown
   or unreadable (`runtime/host_store.py:41-59`), and the `.venv` of each of its worktrees that has
   an `ethos` entry point. The selected runtime's own directory, repo-local or installed, is
   excluded from every writer root, so an adopter whose `runtime/CURRENT` names an installation does
   not defer on itself or on its hooks. Hook generations are not writer roots: hooks exec the
   selected runtime's Python. Other mentions of a path do not count. It reports paths, never command
   lines. Residuals, stated: a relative invocation such as `.venv/bin/python -m ethos` is invisible,
   and a running lane test defers the batch, as it should. A reference that leaves the store, such
   as a digest in a lane commit, stays a residual whose consumers fail closed.
7. **Compare.** Outside the custody lock the apply decodes the members, custody bytes and
   accepted-tree delta added since its last decode, and the kept store files whose name, size or
   mtime changed since, adds their tokens to the run's set and re-closes it; inside one non-blocking
   hold it re-reads the set root and the accepted ref, unlinks the tombstones the set does not name
   and releases, at most 200 unlinks per hold. Each hold repeats when the lock was held or either
   value moved, at most three times, then defers the batch (`custody`); a deferral restores only the
   tombstones not yet unlinked. `_custody_guard` becomes unconditional, so every set swap takes the
   custody lock.
8. **Receipts.** After `sync_directory` of each changed directory, each run writes one
   content-addressed receipt `receipts/record-retirement/<digest>.json`: plan digest, runtime build,
   both cutoffs, per kind the counts and bytes deleted, already absent, kept with reason and
   deferred with reason, and the fact, read after the last batch, that no deleted item's digest is
   among the live members' tokens. A plan is applied only when a receipt without deferrals binds
   it; an apply of it then deletes nothing and reports `already_applied`, as publication does.
9. **Re-link.** `write_content_addressed` tries at most three times: link; on `FileExistsError`
   open, read, compare and `utime`; on `FileNotFoundError` at any step, link again. A third failure
   raises the collision `ValueError`, so callers keep one failure contract.
10. **Residue.** The apply removes each emptied `operations/lane-retirement/<digest>/`. Plans and
    receipts stay owned records of this verb; `record-retirement-kinds` (owner 97f828, next action
    its design after this Change lands, review by 2026-11-15) adds their retention.

## Risks / Trade-offs

- A relative invocation such as `.venv/bin/python -m ethos` is invisible to the writer check, and a
  reference that leaves the store, such as a digest in a lane commit, stays a residual whose
  consumers fail closed.
- A busy store defers batches; the receipt names every deferral, and a rerun continues.
- Size: about +500 to +650 product and +300 to +400 test effective lines; the tests share one
  fixture store.
