---
subject: ethos:decision:release-candidate-gate-successor
role: decision
state: canonical
decision_id: DR-0029
decision_status: accepted
date: 2026-11-15
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
  updates: DR-0026
  updated_by:
    - DR-0030
    - DR-0035
    - DR-0038
---

# DR-0029: The Release Candidate Gate Gains the Law, and Its Dates Become Earliest Dates

Purpose: preserve what the committee of 2026-11-14 changed in the gate that DR-0026 records: the
one item the gate lacked, the dates it withdrew, the rules a batch now lands by, the slip rule, the
rows that moved, and the measures the owner reads.

See also: [DR-0026: The 0.2.0 release candidate gate is recorded with three
waivers](dr-0026-release-candidate-gate.md), which this record succeeds and does not edit;
[DR-0021: Release 0.2.0 declares three journeys](dr-0021-release-scope-0-2-0.md); [DR-0027: Common
semantic structure](dr-0027-common-semantic-structure.md); and the `rc-scope-plan` and
`reporting-obligations` OpenSpec Changes.

## Context

DR-0026 set the candidate for 2026-12-19 on four weekly batches. One day after it was written no
row of its 42 was on `dev`. The first batch stacked fifteen Changes whose own tests passed one at a
time; its first three whole checks failed, twice on one hand-kept table. A rule that arrived
blocking in beta.10, with no earlier report and no repair the product can write, left two governed
repositories unable to prove or land, and no row of the 42 concerned how a rule comes to block.

On 2026-11-14 a committee of five seats (essence, kernel, delivery, fleet, adversary) wrote
independent positions, reviewed one another, voted on two drafts, and signed one resolution with
no blocker in its second merge round. The owner approved three of its decisions the same day.
For this record's subject: `批准，11-19 截止前给我看全文`. For the law freeze:
`是，beta.11 标签前生效`. For the Homebrew attempt: `删除，由继任记录一行写明`.

## Decision

- **DR-0026 stands.** Its rule, its thirteen items and its three waivers are unchanged. Rows left
  on `dev` stay the measure of progress and never the definition of the candidate.
- **R14, the law.** Every rule that can block has a declared state, read through one function. No
  release adds a required gap or a refusal to a tree that passed its predecessor, unless an
  earlier release reported the rule and this release ships its repair. Its first row is the
  `reporting-obligations` Change. The measure becomes 43 rows.
- **Done.** A row is done when its Change is archived on `dev` under a passed full proof of the
  landed tree. Committed, stacked and "lane tests pass" are states.
- **One stack, one whole check.** A batch lands as one stack after one whole check passes at one
  head: the complete impacted set, no failure limit, through the host queue, failures grouped by
  cause before any repair. More than one cause class splits it into units of at most five rows.
- **Entry by the cut.** A row is in a batch only with a converged design and a size measured on
  its patch at the Thursday cut of the week before. Otherwise it moves one batch that day.
- **Derived tables.** A table that restates what the code holds is compared by a check and has one
  integrator; a row that closes a set carries its enumerator.
- **The copies run.** Before each tag, the candidate is moved and proved on a disposable copy of
  every governed tree the releasing host can read, in the selector form that tree holds. No tag
  while a copy shows a new required gap or a new refusal in a tree that passed the predecessor,
  whatever the source, outside R14's one exception: an earlier release reported the rule, and
  this release ships its repair and names it in a Breaking entry. A session other than the
  batch's authors' reads the result, and the entry prints the count for each gap code.
- **The law freeze.** From beta.11's tag to 0.2.0, a narrowing or a ruled defect fix passes. A new
  rule, or a supply move that adds a gap, does not. (Added to by
  [DR-0035](dr-0035-release-candidate-gate-scope.md).) The gate's pin rows are the named exceptions,
  each only in a release whose product ships its repair. (Added to by
  [DR-0038](dr-0038-windows-support-removed.md).)
- **Tags and dates.** Five weekly tags: 2026-11-21, 11-28, 12-05 and 12-12, and a frozen beta on
  12-19 after which no row lands. The candidate is 2026-12-26 at the earliest and the stable release
  2027-01-02 at the earliest: the candidate needs every item's acceptance to hold or be waived,
  every subject bumped to the frozen beta and 72 hours since the last bump; the stable release needs
  seven days since the last bump to the candidate. (Added to by
  [DR-0030](dr-0030-candidate-subject-set.md).) 2026-12-19 is withdrawn as the candidate date. The
  bound that assumes nothing unmeasured, 34 rows at half a row a day, is 2027-01-30, and it is
  stated beside each date. (Replaced by [DR-0035](dr-0035-release-candidate-gate-scope.md).)
- **Lines on `dev`.** At most 33, 24, 15, 6 and 0 rows left on the five tag days.
- **The slip rule.** A row that misses a cut moves one batch by a line on the weekly page, and no
  tag moves. On a tag day when `dev` reads over its line, the next step of the slip order is taken
  that day. When it reads four or more over, the freeze also moves one week and the owner hears it
  that day. (Added to by [DR-0035](dr-0035-release-candidate-gate-scope.md).) On the second such day
  the scope is cut by a successor of this record, and no third date is written.
- **The slip order.** First the cost reducer that makes `status` name the way in; then the release
  time budget and R11's diagnoses with its proof, each by a recorded waiver; then the first-hour
  document, once the install line is in both entry documents; then gate reuse, the offline build
  audit and the two scan rows, each time by the owner's decision, because DR-0026 rejected a
  waiver of gate reuse. The rows that state a rule's state or a tracked pin, the three dependency
  chains, the fast tier, the release rows of R8 and the reference workstation do not leave by this
  order. A row that leaves is a line of a successor record.
- **Homebrew.** The one attempt that DR-0021 allows leaves 0.2.0. The candidate names Homebrew as
  not qualified, without condition.
- **Moves.** The adopter bump moves to the second batch in the owner's full scope, with the handler
  for the older selector form. The retirement of that form lands in the batch after the last pin of
  the derived subject set, and never in the frozen batch. (Added to by
  [DR-0030](dr-0030-candidate-subject-set.md).) `structure-report` follows 0.2.0. So does the move
  of reclamation out of the hook installation: the candidate does not claim that installing the hook
  deletes nothing. One-time repair code gets its own budget category and deletion condition before
  the stable release, by a successor of DR-0010.
- **The weekly page.** On each tag day one page states fifteen measures by command from `dev` at a
  named commit: rows left by reading, rows by state, the landing rate, the free lines under the
  three ceilings, whole checks and proofs of the stack, host minutes declared against used, the
  law by state, new gaps on the copies run, breaking entries by source, pins in, files written by
  hand per bump, CI shapes and repeated checks, rulings by outcome, off-gate rows by class, and
  the next tag with its condition. A value written by hand is marked so until its command exists.

## Alternatives Rejected

- **Define 0.2.0 by five readings in place of the thirteen items:** rejected by three seats because
  it would be a third decomposition beside items and rows. The readings group the rows on the
  weekly page and test what may leave on a slip.
- **Keep 2026-12-19:** rejected by all five seats. It needs four on-time batches at three to four
  times the measured rate, with twelve rows undesigned.
- **Cut the release rehearsal and its admission now:** not taken. They leave only if the stable
  path's owner re-sizes it without them, or if the measured tools lines leave no removal that
  pays for them.
- **Withdraw the blocking rule instead of giving rules a state:** rejected because a special case
  is a second non-blocking path beside the one the audit already has.
- **Land the essence sentence in the contract before 0.2.0:** not taken. The approved placement
  stands; the plan carries the principle from the first batch.

## Consequences and Boundary

- The candidate date is no longer a commitment for 43 rows. No date is restated before the
  checkpoints of 2026-11-21 and 11-28 are read from `dev`.
- A release can be held by a tree that the releasing host reads. The entry states how many trees
  were read.
- Until a verdict is free of its holder, the prover of a unit is its landing owner, and "a session
  other than the author's" separates sessions, not credentials.
- Host minutes are declared like lines, adopters' lanes included.
- This record adds no checker and is not edited after acceptance. A later waiver, a row that
  leaves or a scope cut is a successor record that names this one.

## Evidence and Revisit

- The committee's resolution of 2026-11-14 is a local document; this record is its tracked form
  for the gate. Its fact audit checked 65 claims of the two drafts, and its consistency audit
  scored both against the owner's approved decisions.
- The rate is measured once: 0.45 to 0.5 rows a day. The ceiling projections multiply estimates
  by factors measured on ten rows for tests and one for tools.
- The adopters' gap counts were relayed by the sessions that own those repositories; the copies
  run is their first reproducible reading.

Revisit on a tag day that reads over its line, when the measured tools lines of the release
artifacts' row are known, and when the owner rules on the rows that no order holds. Retire this
record with DR-0026, when 0.2.0 has shipped.
