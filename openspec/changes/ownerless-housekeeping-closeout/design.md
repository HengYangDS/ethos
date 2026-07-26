## Context

After the accepted closeout at
`df5ee833af27c1441aa07083e2c9a97909c799b3`, the complete Work Lane reader
reports ten foreign lanes. Seven have valid leases and remain outside this
Change. Three are clean, linked, missing both lease and Claim binding, and are
diverged from accepted truth:

| Branch | Exact HEAD | Current semantic relation |
| --- | --- | --- |
| `work/20260724-20260724-budget-contract-v2-changed-scope-source-admission` | `8afc80fd78a3d2c80144ae3d93d4045a004f3f54` | Exact ancestor of five valid-owner source-admission successors. |
| `work/20260725-budget-contract-v2-changed-scope-source-admission-successor` | `8d0691b7f84b89f549b211f533c5fa2d017edcfc` | Exact ancestor of the same five valid-owner successors. |
| `work/20260724-release-0-1-0a2` | `a3d5329a4b6d0660d62faa738aaf66a244b9e219` | One unique release-date commit, reachable from no other branch or tag and not accepted. |

Ordinary landed and superseded retirement correctly reject all three because
they are foreign, diverged, and not accepted-absorbed. Native exceptional
resolution therefore requires accepted, target-bound Chronicle evidence.

## Goals / Non-Goals

**Goals:**

- Give each currently actionable ownerless lane one exact, accepted disposition.
- Preserve all unique release intent before source removal.
- Compress predecessor refs without granting any mutation authority over the
  valid-owner successor lineage that retains their commits.
- Repair the stale final-state wording in the native-resolution Claim and
  Chronicle using already verified exact-HEAD closeout evidence.
- Finish with reviewed cache-only and ignored-bytecode cleanup.

**Non-Goals:**

- No mutation, handoff, land, retirement, or semantic completion claim for any
  valid-owner lane.
- No branch-wide merge or cherry-pick from historical predecessor topology.
- No remote probe, push, tag/release publication, hosted claim, raw Git cleanup,
  SQLite edit, or recovery-package clear.

## Decisions

1. **Use one target-bound Chronicle and Claim per source.** Each front matter
   binds one event, literal branch, and exact HEAD. A changed branch, HEAD,
   lease, Claim, dirtiness, or worktree binding invalidates that target only.

2. **Select direct retire for the two lineage-retained predecessors.** Their
   exact commits are currently ancestors of all five valid-owner successors.
   This reachability is evidence that the historical commits are retained, not
   authority over those successors. Native effect admission still owns the
   accepted-ancestor boundary. If it returns a no-effect block, this Change
   does not silently switch dispositions; a later accepted reconciliation must
   explicitly select the transient `preserve-retire` bridge.

3. **Select preserve-retire for the unique release lane.** Its one commit changes
   three release-date references from the accepted `2026-07-24` conclusion to
   `2026-07-25`. The repository does not accept that date through housekeeping.
   Native preservation must verify the bundle, patches, manifest, and receipt
   before removing only this source ref and worktree. The package remains
   retained recovery evidence.

4. **Apply effects serially.** Every target follows fresh observation, decision
   dry-run, decision write, effect dry-run, exact apply, receipt verification,
   and full re-observation. Two irreversible transitions never overlap in the
   shared Git common directory.

5. **Repair claims without upgrading evidence classes.** The existing native
   resolution Chronicle may append the completed proof, closeout, local publish,
   and task-lane retirement facts. It must continue to state that remote push,
   remote availability, hosted CI, and whole-repository terminal completion are
   unproved.

6. **Treat generated residue as generated residue.** After tracked lifecycle
   completion, remove only the reviewed unregistered `.pytest_cache`, empty
   tool-cache directory chain, and exact ignored WCP bytecode files. Foreign
   worktrees, environments, state SQLite, historical records, and IDE/session
   state remain untouched.

## Risks / Trade-offs

- **A valid-owner successor rewrites away a predecessor** → Stop that target and
  regenerate the accepted semantic decision; do not infer retention from the
  branch name.
- **Direct retire reaches the native accepted-ancestor boundary** → Preserve the
  no-effect result and use a separate accepted reconciliation carrier before a
  transient preserve-retire bridge.
- **Release package creation or verification fails** → Keep the branch and
  worktree intact; retain only native failure evidence.
- **A lease or dirty overlay appears** → The target becomes foreign active work
  and is excluded from this closeout.
- **Cache cleanup path drifts** → Skip deletion; absence is not inferred from a
  parent directory or broad glob.

## Migration Plan

1. Validate and archive this authority carrier, obtain exact-HEAD executed
   proof, land to candidate, and perform sanctioned accepted-root closeout.
2. Re-observe all three targets and the five valid-owner successor heads.
3. Decide and apply one target at a time through native lane resolution.
4. If either direct-retire target records the expected no-effect boundary,
   create a separate minimal reconciliation carrier before changing its
   disposition.
5. Verify resolution inventory, retained release package hashes, protected
   refs, and valid-owner lane identity.
6. Run native detached housekeeping; apply only a non-empty admitted set. Then
   remove the separately reviewed non-Git caches and exact bytecode residues.

Rollback before an effect is to leave the source untouched. After a successful
preserve-retire effect, recovery is from the verified package; raw ref or
worktree reconstruction is not part of this Change.

## Open Questions

None. Mutable target observations are execution-time predicates rather than
open design choices.
