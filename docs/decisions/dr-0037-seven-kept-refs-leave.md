---
subject: ethos:decision:seven-kept-refs-leave
role: decision
state: canonical
decision_id: DR-0037
decision_status: accepted
date: 2026-11-26
relations:
  current_owner: ../../openspec/specs/repository-governance/spec.md
  updates: DR-0034
---

# DR-0037: The Seven Kept Refs Left Open by DR-0034 Also Leave

Purpose: record, for each of the seven kept refs that DR-0034 left undecided, what it holds that
`dev` lacks and why none of it is kept, and the owner's decision that all seven leave.

See also: [DR-0034: A Kept Item Has a Consumer and an Exit, and Five Kept Refs
Leave](dr-0034-kept-items-have-a-consumer.md), whose rule this record applies.

## Context

DR-0034 decided that five snapshot refs leave (they were deleted on 2026-11-22), kept the three
history-repair originals that the product reads, and left seven refs undecided. Each of the seven
holds one commit whose content `dev` lacks, beside 3 to 2,385 older commits of the history before
its repair, whose content `dev` holds. DR-0034's rule, with `dev` as the accepted history: content
that `dev` lacks is absorbed or withdrawn by a record before it leaves. No file, command or test
reads any of the seven by name.

## Decision

- **All seven leave**, by the owner's decision of 2026-11-26. The release lead put three options to
  him and recommended the first: delete all seven; delete four and keep `candidate-legacy-proof`,
  `cutover-hardening` and `foreign-dirty` to an expiry date; keep all seven to an expiry date. He
  took the recommendation. What each holds that `dev` lacks is withdrawn by this record, not
  absorbed: in meaning it is superseded by what `dev` later became, as the last column shows.

| Ref                                                                      | Tip            | What it holds that `dev` lacks                                                                 | Why it is not kept                                                                                                                                                                                  |
| ------------------------------------------------------------------------ | -------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `refs/keep/codex/complete-post-publication-governance-20260709`          | `f7d20452f352` | one change of `evidence/parity/generic-shadow.json` (18 lines replaced by 18)                  | the file and its directory `evidence/` were removed from `dev` entirely                                                                                                                             |
| `refs/keep/codex/complete-post-publication-governance-20260710-recovery` | `2b58fd0bea7b` | the same file, another regeneration                                                            | as above                                                                                                                                                                                            |
| `refs/keep/codex/complete-post-publication-governance-final-20260710`    | `83558cda7a69` | the same file, another regeneration                                                            | as above                                                                                                                                                                                            |
| `refs/keep/terminal-convergence/candidate-legacy-proof-ae47420531fb`     | `070674a4246f` | an archive of 452 cached proof files with its manifest                                         | its manifest declares `"authority":"none"`: by its own statement it is not evidence                                                                                                                 |
| `refs/keep/terminal-convergence/cutover-hardening-20260728T141416Z`      | `3b77641b7d32` | one version of the module `successor_cutover.py` (534 lines) and its test                      | `dev` added the module on 2026-07-28 and removed it the next day (`dc3dc1ebe`, "erase successor bootstrap")                                                                                         |
| `refs/keep/terminal-convergence/foreign-dirty-20260728T141900Z`          | `2c28d757a01e` | the uncommitted changes of a retired work branch: a patch over 13 files and 12 untracked files | 24 of the 25 paths no longer exist on `dev`; the 25th, `openspec/specs/repository-governance/spec.md`, changes one scenario title that `dev` no longer has; the branch's committed part is on `dev` |
| `refs/keep/terminal-convergence/successor-20260728T135612Z`              | `610a82cd5e8f` | one version of `tests/unit/kernel/test_commitment_carrier.py` (236 lines, 9 tests)             | `dev` added its successor the next day (`7f52fda09`, all nine test names, 9 lines different), changed it 12 times and removed it on 2026-08-29                                                      |

- **The three history-repair originals stay**, as DR-0034 decided.

## Alternatives Rejected

- Keeping `candidate-legacy-proof`, `cutover-hardening` and `foreign-dirty` to an expiry date, or
  all seven. Either was within the owner's rule, which lets a kept item stay until a stated expiry
  date; he chose deletion. A date would only have deferred it: what each holds is superseded as the
  table says, and no consumer was found for any of the seven.
- Absorbing the uncommitted patch of `foreign-dirty`. It changes files of a layout
  (`packages/ethos/…`) that `dev` later replaced whole; 24 of its 25 paths no longer exist, and the
  one change to the 25th is to a scenario that `dev` no longer has.

## Consequences and Boundary

Deleting the seven frees 5,023,047 bytes (1,585 objects) of this repository. Each deletion is an
ordinary Git deletion with its expected old value, so a ref that moved is not deleted. After Git's
collection the seven tips cannot be recovered: neither Forge holds them (read on 2026-11-26), and no
other copy is known.

The deletion rests on one assumption: the recoveries for which `candidate-legacy-proof`,
`cutover-hardening` and `foreign-dirty` were taken are finished or no longer needed. No record
states that any of them finished; what was found is the table above. A recovery that still depends
on one of them cannot be done after the deletion. The patch of `foreign-dirty` (378 lines added, 445
removed) was compared with `dev` by its paths, not line by line: whether an idea in it is missing
from today's code was not checked.

The product counts every ref under `refs/keep/` as one that keeps its commits when it cleans
detached worktrees. At the later reading of 2026-11-26 the repository's three worktrees were all on
branches, so the deletion is judged not to change that cleanup; this was read from the code, not
run.

## Evidence and Revisit

The repository's owner decided on 2026-11-26. Read that day at `dev` `39a1a8ffc`: each ref's commits
with no patch-equal commit on `dev` (Git's cherry comparison), and for those commits their files
compared with every version in `dev`'s history. Later that day the seven tips were unchanged and
neither Forge held a ref under `refs/keep/`; `dev`, then at `cdb51d469`, had changed only the
version, the changelog, known-defect entries, a release binding and one test since `39a1a8ffc`. The
release lead's working notes hold the full reading; they are local and not kept. Within the hour
before the deletion these readings are taken again; any difference stops the deletion and goes back
to the owner. Revisit before the deletion if that reading finds a difference, or a consumer or an
unfinished recovery that depends on one of the seven; after Git's collection the decision cannot be
reversed.
