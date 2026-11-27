---
subject: ethos:decision:kept-items-have-a-consumer
role: decision
state: canonical
decision_id: DR-0034
decision_status: accepted
date: 2026-11-21
relations:
  current_owner: ../../openspec/specs/repository-governance/spec.md
  updated_by: DR-0037
---

# DR-0034: A Kept Item Has a Consumer and an Exit, and Five Kept Refs Leave

Purpose: preserve the owner's rule for anything kept outside the accepted history, the evidence
that five kept refs of this repository hold nothing that the accepted history lacks, and which
kept refs this record does not cover.

See also: [DR-0013: Historical repair evidence reads its own policy
location](dr-0013-historical-repair-policy-location.md), under which the product verifies a
recorded repair from the kept originals.

## Context

A kept ref (`refs/keep/...`) stops Git from collecting commits that no branch or tag holds. On
2026-11-21 this repository held 15 of them, none made by the product: three originals of history
repairs, three left by a session on 2026-07-10, and nine snapshots left during the convergence
of July and August. The owner's words: keeping without absorbing piles up waste (2026-11-20);
kept things may only decrease (2026-11-21); and what a higher form has absorbed, covered or
corrected need not be kept, once that is established before the deletion (2026-11-21).

## Decision

- **The rule.** An item is kept outside the accepted history only with a named consumer and the
  condition under which that consumer releases it. An item without both is not kept. An existing
  item is judged by its meaning: absorbed or superseded content leaves; content that the
  accepted history lacks is absorbed or withdrawn by a record before it leaves.
- **Five snapshot refs leave**, under `refs/keep/terminal-convergence/`:
  `hardening-prepare-20260728T143400Z` (`8deac1fec`), `hardened-successor-20260728T144000Z`
  (`fc88267e7`), `hardened-successor-v2-20260728T145500Z` (`f3ca47cae`),
  `monotonic-prepare-p0-prepatch-20260728T152500Z` (`0b1204a2b`) and
  `hardened-successor-v3-20260729T001100Z` (`e3bc687e5`).
- **The three history-repair originals stay.** Their consumer is the product, which verifies a
  recorded repair from the commits before it; they leave when the product no longer reads them.
- **Seven kept refs are not decided here**: the three of 2026-07-10 and four snapshots
  (`candidate-legacy-proof`, `cutover-hardening`, `foreign-dirty`, `successor`). Each holds one
  commit whose content the accepted history lacks. (Added to by
  [DR-0037](dr-0037-seven-kept-refs-leave.md).)

## Alternatives Rejected

- A default lifetime in days. It measures how long an item was kept, not whether its meaning is
  still needed.
- Merging the snapshots into the accepted history. They are whole trees of July, and the accepted
  history already holds every one of their commits' content.

## Consequences and Boundary

The five deletions are ordinary Git deletions with the expected old value; the product records
nothing for a kept ref. After Git's collection the five tips cannot be recovered on this host.
The rule binds this repository's sessions; a product function that enforces it is a new rule and
is not part of this record.

## Evidence and Revisit

Read on 2026-11-21 at `dev` `024c217bf`, and again on 2026-11-22 at `eee24a887` with the same
answer:

- Every commit of the five refs after their merge-base with `dev` has a patch-equal commit on
  `dev` (Git's cherry comparison of each ref with `dev` lists none as missing): 1,672, 1,673,
  1,674, 1,675 and 1,677 non-merge commits.
- For three of them every commit's root tree, merges included, is the root tree of a `dev`
  commit; the tips' trees are those of `6c3b24583`, `3f1bae8ed` and `7f52fda09`.
- The tips of the other two share no root tree with a `dev` commit. Each is rebuilt bit for bit
  from objects that `dev` holds: the tree of the tip's parent is the tree of `6c3b24583`
  (respectively `d49b508e9`), the tip's change is the change of `dev`'s `7f52fda09`, and the
  merge of the two gives the tip's tree (`9f2721a9a4f2`, `65808ae9b0d4`).

The precondition is read again in the hour of the deletion; one difference stops it. The seven
undecided refs are put to the owner by class.
