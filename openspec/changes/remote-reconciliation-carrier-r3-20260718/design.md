## Context

The local , , and  refs start aligned at
. Fresh read-only observation records GitLab  at ,
GitLab  at , GitHub  at , and GitHub
 at . The repository already separates candidate and
accepted transitions from remote publication and hosted-provider observation.

## Goals / Non-Goals

**Goals:**

- Preserve every observed protected remote history through ordinary merge
  commits.
- Produce one HEAD-bound local proof before any protected-ref update.
- Use only ordinary non-force push attempts and re-observe each provider after
  every update.
- Retain a bounded Chronicle that states what is observed at each stage.

**Non-Goals:**

- No rebase, reset-based ref movement, stash-based conflict bypass, force push,
  release, version change, or tag.
- No claim that local proof establishes remote equality or hosted CI success.
- No mutation of foreign Work Lanes or their artifacts.

## Decisions

1. **Fresh inputs bound each remote horizon.** The four 294875daff72310c075fca3567c8b5db14a135b0	refs/heads/dev
6e3074fca38c00a7f7dfa3c95c0de1ed870b0b19	refs/heads/main
d271934a9b490fc91acbc6b6b5fdd2bc3e726308	refs/heads/submit/hosted-ci-remediation-20260717
   values are captured before merge planning and checked again before push. A
   changed input invalidates the current merge and push plan.
2. **Ordinary merges preserve history.** The reconciliation head must be a
   descendant of each recorded tip. A conflict resolution is an explicit source
   choice, not a ref rewrite.
3. **Evidence remains partitioned.** Executed local proof, local closeout,
   remote ref equality, and hosted-provider status are observed independently.
4. **The Lane is claim-bound before merge execution.** The carrier prevents an
   untracked operational change from becoming the closeout narrative.

## Risks / Trade-offs

- **A remote tip changes while work is in progress** -> refresh the input set
  and rebuild the merge/push plan.
- **A merge conflict exposes an obsolete provider carrier** -> retain parents,
  review the source choice, and stop if no safe resolution exists.
- **A provider rejects a protected update or CI is unavailable** -> retain local
  evidence and report remote or hosted state as unconfirmed.

## Migration Plan

1. Bind the owned Work Lane to the active claim and explicit scope.
2. Merge all fresh observed tips with normal merges only.
3. Run parity, changed-plan, and HEAD-bound proof; complete candidate and
   accepted local transitions.
4. Run per-ref push dry-runs, ordinary updates, remote re-observation, and
   separate hosted-provider observation.
5. Archive the carrier only after all task and evidence states are current.
