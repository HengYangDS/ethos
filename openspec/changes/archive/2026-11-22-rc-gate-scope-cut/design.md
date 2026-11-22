# Design

## Context

The proposal holds the text that the committee signed and the owner approved. This design holds
what stands behind it: the test that decided each row, the reasons, where the five seats
differed and how each difference was settled, and what nobody proved. The committee's working
files are local to the releasing checkout; this is their tracked form.

The question came from the release lead on 2026-11-17. Design studies for the batch of 0.2.0-beta.13
had found the plan's rows larger than the sizes the plan gave them: of nine studied rows only a
first slice fits its batch, and the first slices alone pass the test ceiling. The lead brought the
smallest proposal, by the owner's answer of that day: move out only the parts that cannot take
effect inside the freeze. Five seats answered in three rounds: essence (ess), kernel (ker), delivery
(del), fleet (written in full) and adversary (adv). Four signed the second text, the adversary
blocked it with two exact changes, and all five signed the third.

Names below: `S` is DR-0029, `G26` is DR-0026, `P` is the design of the release candidate plan,
`PDC` is the product design contract and `QS` is the quality specification, each with the line
numbers read on 2026-11-17. b13 and b14 are the batches of 0.2.0-beta.13 and 0.2.0-beta.14.

## Goals / Non-Goals

**Goals:**

- State for each of ten rows which part 0.2.0 requires and which named remainder follows it.
- Keep the measure of 43 rows true: a slice is never counted as a row.
- Correct the plan's words where a study showed them untrue, without editing the archive.

**Non-Goals:**

- No tag date changes and none is restated. No refusal arms and no default flips before 0.2.0.
- No word of DR-0026, DR-0029 or the archived plan changes. The two records gain the relation
  and the marks of the decision-record form, by sentence as DR-0026 already carries them, and
  the record succeeds them.

## Decisions

### 1. The test that decides a part

A part must land for 0.2.0 when its item's sentence in `G26` is false without it (adv, ker, del),
or when a governed repository needs it to bump, prove, land, publish or roll back (fleet). The
lead's smallest proposal is the floor and is not enough: a part whose only reader leaves goes
with that reader, and a remainder that size and time keep out leaves by name. Four seats kept
the proposal as the floor. The adversary did not accept its wording: what leaves a sentence of
`G26` false leaves by a named waiver and not as an effect of the freeze.

Not taken: a cut by size. Size and time may be why a remainder cannot land, and they are never
the written reason (ess, adv). A remainder leaves by name, as a cut of scope (del, fleet).

### 2. How a remainder leaves

By a line of the successor record where the item's sentence in `G26` holds without it, and by a
waiver where it does not: Waiver 4 for the bound receipt of a rehearsal, and the waiver of R7 on
a condition for `residue-class`. The measure stays 43 rows, 42 by that waiver. Done is defined
once: every kept part is archived on `dev` under a passed full proof (`S`:49-50).

### 3. The ten rows

| Row                     | Must land for 0.2.0 (b13; b14)  | Follows 0.2.0              | Note |
| ----------------------- | ------------------------------- | -------------------------- | ---- |
| `fast-tier`             | report; the selection's run     | late gates, recorded facts | n1   |
| `gate-environment`      | report, contract text; cache    | state, redaction, keys     | n2   |
| `rollback-after-repair` | record; the pin's receipt       | landings, Mise             | n3   |
| `residue-class`         | whole, one unit, cut of 12-03   | none; or whole, by waiver  | n4   |
| `release-rehearsal`     | platforms, assembly, journey    | bound receipt (Waiver 4)   | n5   |
| `rehearsal-admission`   | report (b14); opt-in            | record, command, refusal   | n5   |
| `gate-reuse`            | key, record, comparison; arming | the split of the test gate | n6   |
| `store-retention`       | release, report; `status` word  | three record kinds         | n7   |
| `proof-output-scratch`  | reader, footprint; registry     | a dead owner's scratch     | n8   |
| `release-provenance`    | the whole row                   | not placed: no study       | n9   |

Before a semicolon stands b13's part, after it b14's. A remainder may still land when a cut
measures its patch (ess, del).

- n1. `G26`:67 asks for "a fast behavior tier", and a report runs no test (ker, del, fleet, adv).
  The run is under a host ticket (adv). The row `test-tiers` of the plan is not one of the 43.
- n2. R8's "or" holds only when the contract states the boundary (`G26`:78-79), so the row's
  Change amends `PDC`:403-404 and the owner sees the text in the report's batch (ess, ker, fleet).
  The cache root is b14's. The state ships one release before its default (ker).
- n3. R4 "is exercised" (`G26`:63); once every subject declares a pin, the pinned shape is the
  one in use (ess, fleet, adv). The receipt needs 0.2.0-beta.11 published. The entry names the
  landings as not qualified (ess, adv); the fleet seat lowered its blocker: one run by hand lands
  them before the candidate.
- n4. The second way of the row's study with its second slice, never its first slice alone (ker,
  del, adv). With no patch measured at the cut of 2026-12-03 it leaves whole by the waiver.
- n5. The bound receipt's one reader is the refusal's command (ker, ess, adv), so both leave by
  Waiver 4, a waiver of `G26`:62 and no effect of the freeze (adv, ker, del). The report refuses
  nothing, and ETHOS opts in once its pin reads the key (adv, ker).
- n6. A gate arms on its own record, at a threshold written before any count is read (ess, adv),
  only if its key is closed and it starts no child but Git (ker), with records from three
  governed repositories (fleet), never in the frozen beta (del, fleet).
- n7. R7's budgets report; a refusal for bytes is a new rule (ess, fleet; `G26`:74). The 48 hours
  are two windows of real workload, or a delta changes `QS`:1896-1900 (adv).
- n8. `G26`:73, "Lanes stop holding gate evidence", needs the registry's move (ker, adv). No tree
  declares `{scratch}` before its pin reads it (ker).
- n9. An unread row moves no part (ess, ker, adv): its study and size are due at the cut of
  2026-11-26 (fleet).

### 4. Dates, lines and the bound

- **Tags.** Unchanged, by the weekly calendar and by no rate (`S`:67-71): 2026-11-21 on the
  owner's word, 11-28, 12-05, 12-12 and the frozen beta on 12-19. Earliest candidate 12-26,
  earliest stable release 2027-01-02.
- **Lines.** 33, 24, 15, 6 and 0 stand (`S`:74). The line of 33 rests on ten rows archived on
  `dev`; the line of 24 rests on the nine rows of 0.2.0-beta.12, reviewed and not landed.
- **The rule.** `S`:75-79 as written, and one line more: when the freeze moves one week on a tag
  day, the line read that day and each later line move one tag day (del, adv). `S` writes no line
  for the added week; without the sentence 12-12 is a second day that reads four over (del).
- **The forecast for 12-05, an inference.** `dev` reads 22 to 24 against 15 if the nine rows of
  0.2.0-beta.12 have landed: by the table at most two rows of b13 are done that day, and seven
  rows keep a part for b14. The rule then moves the freeze to 12-26, the candidate to
  2027-01-02 and the stable release to 01-09, on that day's reading alone.
- **The bound.** 2027-01-30 was 34 rows at half a row a day (`S`:72-73). The rate was measured
  once, on the seven days to 2026-11-13, and rows read two to nine times their plan size in
  tests. It is no bound (del, adv): one is printed from two tag-day readings of `dev`.
- **Cuts and budgets.** 2026-11-26 for `release-provenance`, 12-03 for b14, 12-10 for the frozen
  beta. A kept part that misses its cut slips by `S`'s rule. The product ceiling goes to the
  owner at the cut of 12-03, on patch sizes (del). Host minutes are declared before each whole
  check (del, fleet).

### 5. Corrections of the plan's words

The archived plan is not edited (ess); the successor record states each correction.

1. `P`:476-479: no published predecessor since 0.2.0-beta.6 refuses a rollback after a repair,
   and the open state is `runtime_selection_open`. The leg records what the product decides.
2. `P`:426-427: a pin to an unpublished candidate cannot be followed, so the rehearsal's
   restore-then-rollback step is the published journey's.
3. `P`:438-442: the Attestation is `release:rehearsal`, and 0.2.0 reports where the plan said
   that a release landing refuses.
4. `P`:106-107: the fast tier adds no tests to readiness; a gate there is a new refusal.
5. `P`:93-94: byte budgets report (`G26`:74 has no word of refusal). The parameter of the store
   budget had no reader when the committee sat.
6. `P`:108-109 and `QS`:1775-1787, the 900 seconds: no cold proof meets them; one gate alone
   took 1,264.6 seconds in the study. Amended by the frozen beta, only with a figure measured on
   the declared reference host (ess, adv).
7. `P`:148-149 and 172-178, the sizes: no input to a date (del). A size is read on a patch at a
   cut.
8. `residue-class` as a row that replaces its root's nodes ships a refusal; the second way of
   its study refuses nothing.
9. "D.1 to D.4 landed": publication requests, superseded units, the retention verb's own records
   and the `status` sentence are not built.
10. `G26`:136-137, reuse "makes a pin-only bump cheap": no sound key does, and 11 of 34 gates
    have no closed inputs (ker). No second is saved before the frozen beta (del).
11. `PDC`:403-404, "not ambient `PATH`": a declared command resolves on the launch path and its
    child inherits the launch environment; 26 of 32 declared command gates start a bare tool.
12. The selection from recorded facts belongs to `fast-tier`, not to `test-tiers` (adv).
13. `P`:117 and 325-326: the runner of a detached run starts in the launch environment in
    0.2.0, and its list follows with the state (fleet).

### 6. The five asks and the owner's answers

Each ask named its options and the committee's recommendation. The owner answered on 2026-11-17
with the recommendation of each.

1. **Waiver 4.** Granted: a release of 0.2.0 can land unrehearsed, and receipt, command and
   refusal follow it. Not taken: refuse the waiver, by which R4 holds the candidate.
2. **Is a report a new rule of the freeze?** No. Not taken: yes, by which three reports leave
   the freeze and two decisions of the same day are taken back.
3. **The split of the test gate.** It follows 0.2.0: reuse then arms on gates of 0.4 to 29.2
   seconds, as the study's spike measured them, and saves almost no second in 0.2.0. Not
   taken: it stays, about 1,111 seconds saved by estimate, armed in the frozen beta against
   the kernel seat's condition.
4. **`residue-class`.** One unit with the waiver on a condition: about +335 product and +350
   test lines by estimate, for about a second a review. Not taken: it leaves now; or no exit,
   by which a miss slips and may move the freeze.
5. **The list-built child as a state.** After 0.2.0, its default one release later. Not taken:
   in b14, about 170 product and 260 test lines by estimate, with a flip at the first release
   of 0.3.0.

### 7. Where the seats differed, and how each difference was settled

1. The smallest proposal: four seats' floor; the adversary not as worded. Kept, with Waiver 4.
2. Essence let the selection's run, the `status` word and the registry's move leave; four seats
   kept them. Kept.
3. Rollback: the record (ker, del), the receipt (ess, adv), the revert (fleet). The receipt.
4. The bound receipt: del and fleet kept it in b14; ess, ker and adv moved it with its reader.
   Moved.
5. `residue-class`: fleet out now; ess, ker and del by a cut; adv never. The fourth ask.
6. Lines: ess and ker added nothing; del and adv moved them; fleet redrew them by the rate. The
   one added sentence, by vote.
7. 2027-01-30: del and adv withdrew it; ess kept it by each date. Withdrawn.
8. The list as a state: adv kept it; ker, del and fleet moved it; ess let it leave. The fifth ask.
9. Record kinds: adv owed all; ker kept the verb's own; ess, del and fleet moved three. Three.
10. A kept part that misses its cut: del had it leave; ess, fleet and adv held it. It slips.
11. A report inside the freeze: no seat wrote the sentence. The second ask.
12. The frozen beta: fleet barred any first effect; del barred arming; ker had a row in it. Arming
    is barred.
13. The 900 seconds: ker in b14, ess by the frozen beta, fleet at arming, adv measured. The sixth
    correction.
14. The cut of `residue-class`: del 12-03, ker 12-10. 12-03, its next cut, by vote.
15. The forecast for 12-05: ker 20 or 21 by its own table; del, fleet and adv 22 to 24 by the
    table above. By the table.

## Risks / Trade-offs

- [Every size but one is an estimate] -> Only `fast-tier`'s first slice was measured when the
  committee sat. A kept part names the cut that measures its patch.
- [The forecast is an inference] -> It counts by the table and takes the nine rows of
  0.2.0-beta.12 as landed by 2026-11-28. The freeze moves on a tag day's reading, never on it.
- [No seat ran a test, a proof or a spike] -> The seats read studies, reports and decisions.
  No seat read the study of `residue-class`, and fifteen of the 24 rows that follow have none.
- [Whether the kept parts fit the product ceiling] -> The nine studied rows whole are about
  2,200 to 2,537 product lines by sums of estimates, against 2,178 free. The owner reads the
  ceiling at the cut of 2026-12-03.
- [0.2.0 lacks what the waivers name] -> A refusal of an unrehearsed release, and, on the
  condition, the review derived at a landed retirement. Each has a named replacement by hand.
- [Wording that no seat wrote] -> The sentence on a report inside the freeze and the parts of
  the waiver of R7 are the clerk's, signed by all five.
