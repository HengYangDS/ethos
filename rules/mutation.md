# Mutation Rules

Purpose: define tracked write admission and Work Lane discipline.

| Field | Rule |
| --- | --- |
| Authority | `ethos status --json`, `ethos lane prewrite --json`, [Runner And Mutation](../docs/architecture/runner-and-mutation.md) |
| Trigger | Any tracked file write, generated tracked output, or command with tracked mutation potential. |
| Action | Resolve the worktree, actor, branch role, Lease, fresh Git facts, and exact ref intent before mutation. |
| Evidence | `ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json` returns `verdict=pass`. |
| Stop | Protected root, candidate checkout, detached checkout, stale editor root, root-binding mismatch, or path outside target root. |

## Rules

- Public mutation authorization is the closed `verdict` union `pass | block | unknown`; only `verdict=pass` authorizes an effect. Missing or unverifiable required facts produce `unknown`; conflicts, explicit failures, and warnings produce `block`.

- Normal tracked mutation belongs only in an owned `work/*` Work Lane.
- `accepted_root` and `candidate` checkouts are observe-only for normal edits.
- Before writing, run `ethos status --json` and `ethos lane prewrite`.
- Official OpenSpec is the sole tracked intent carrier. ETHOS compiles its exact
  selected projection into a transient Commitment containing only
  `schema_version`, `id`, and `acceptance`.
- A Lease records only `lane_ref`, `holder_ref`, `generation`, and `expires_at`.
  It never stores Git coordinates, paths, OpenSpec identity, Commitment,
  workflow progress, handoff state, or effect outcome.
- Every mutation observes fresh HEAD, tree, index, worktree, and ref facts;
  compiles one exact ref intent; rechecks those facts at effect time; applies one
  compare-and-swap; then post-observes and attests.
- Archive and lane creation invoke the official OpenSpec operation and Git
  effect as one bounded transition. They do not create a second intent carrier,
  predicted path scope, or command-specific authority record.
- Write-capable tools must carry an explicit target root or working directory
  matching the admitted Work Lane. Do not rely on the host launch context's default
  filesystem path for tracked writes.
- When no `--root` is supplied, ETHOS commands bind to the current Git worktree
  root, not an accepted-root checkout or host launch directory.
- Product-repository mutation admission must fail closed when the command
  runner, schema source, editor root, and audited root do not describe the same
  checkout.
- If a write tool cannot bind actor, target root, branch role, Lease, fresh
  facts, and exact target ref before mutation, it must not write.
- A failed transition leaves the observed Git ref, index, worktree, and Lease
  unchanged or emits sufficient effect evidence for deterministic recovery.
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
