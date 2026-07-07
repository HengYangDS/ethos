# Mutation Rules

Purpose: define tracked write admission and Work Lane discipline.

| Field | Rule |
| --- | --- |
| Authority | `ethos status --json`, `ethos lane prewrite --json`, [Runner And Mutation](../docs/architecture/runner-and-mutation.md) |
| Trigger | Any tracked file write, generated tracked output, or command with tracked mutation potential. |
| Action | Resolve the Git worktree root, classify branch role, bind runner/schema/editor roots, and run write admission before mutation. |
| Evidence | `ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json` returns `ok=true`. |
| Stop | Protected root, candidate checkout, detached checkout, stale editor root, root-binding mismatch, or path outside target root. |

## Rules

- Normal tracked mutation belongs only in an owned `work/*` Work Lane.
- `accepted_root` and `candidate` checkouts are observe-only for normal edits.
- Before writing, run `ethos status --json` and `ethos lane prewrite`.
- Write-capable tools must carry an explicit target root or working directory
  matching the admitted Work Lane. Do not rely on the chat session's default
  filesystem context for tracked writes.
- When no `--root` is supplied, ETHOS commands bind to the current Git worktree
  root, not an accepted-root checkout or host launch directory.
- Product-repository mutation admission must fail closed when the command
  runner, schema source, editor root, and audited root do not describe the same
  checkout.
- If a write tool cannot bind target root, branch role, editor root, and target
  paths before mutation, treat it as degraded mode and run explicit prewrite
  immediately before the write.
- If protected-root mutation is detected after the fact, stop normal work. The
  change must be classified before any further product work: useful work is
  absorbed into an owned Work Lane with visible evidence, and useless or unsafe
  pollution is reverted from the protected root. Only rollback, migration to a
  Work Lane, recovery evidence, or violation reporting is allowed until the
  protected root is clean.

- Do not use `git stash` as a backup, handoff, residue, or closeout carrier.
  Dirty work must either be absorbed into an owned Work Lane with visible
  evidence or reverted from the protected root after classification.
- Accepted-root closeout is not normal editing. It must run through audited
  closeout command semantics.
