# Design

## Context

See the [proposal](proposal.md). The ten gate rows of 0.2.0-beta.11 are archived on `dev` under
passed full proofs, and DR-0029 sets the tag for 2026-11-21. A release is cut from accepted source
by the release guide: a release Change moves the version and curates the entry, lands, and the
tag is created at that accepted head after both forges qualify it.

## Goals / Non-Goals

Goals:

- One release Change that moves the version, writes the release entry and records the steps that
  a tag needs.
- The copies run complete on the release head's candidate before the tag, or each tree it could
  not prove named with its reason.

Non-Goals:

- Any gate row. The rows of 0.2.0-beta.12 land after the tag.
- The weekly page's commands. A value read by hand is marked so.

## Decisions

1. **The release head is the last landing before the tag.**
   - **Rests on:** the release guide, whose tag is created at the accepted head that the release
     Change landed; DR-0029's rule that the candidate is proved on a copy of every readable tree
     before the tag.
   - **Considered:** landing prepared rows of 0.2.0-beta.12 before the tag, which would put them
     into this release without a copies run on their head.
   - **Chosen because:** the copies run stands for one head, and a new product change starts it
     again. Accepted: nothing but this lane lands on `dev` before the tag.
   - **Applies to:** `dev` from this lane's landing to the tag. Work in lanes and proposal refs
     continues.
2. **The repairs of the release diff's review land in this lane, before the version moves.**
   - **Rests on:** the model review of 2026-11-15 over the diff from the previous release to
     `dev`, 83 files of product, tools and configuration. It returned 13 leads; each repair
     Change states, for its leads, the regression that decided them. Among the real ones is a
     regression of this batch: a run that stops waiting for the host queue left its ticket.
   - **Considered:** a lane of their own before this one, which the release guide's first step
     describes; it needs a second full proof, about 100 minutes from launch to end on the shared
     host on 2026-11-15, and a second candidate for the copies run. Also considered: the tag
     without them and the repairs in the next release, which ships a known regression to every
     governed repository.
   - **Chosen because:** the repairs are part of what this release ships, the two previous
     releases also closed the lane of their last Changes, and one proof keeps the one candidate
     whose product tree is the release head's.
   - **Applies to:** the four repair Changes of this lane. Each keeps its own Change, commits
     and archive. The lead on the journey's negative cases is a known open defect of the entry,
     and its repair rides with the journey's row of the next batch. Two real leads are carried
     forward and not repaired here: gap codes that only a family registers, whose exact rule
     needs up to 109 rows by the repair's measurement (draft `gap-code-literals`), and a version
     accepted again across its checksum binding, whose transition has no caller in this release
     (the follow-up of `release-trust-repairs`).
3. **The reader gets the packaged candidate that this lane's proof keeps.**
   - **Rests on:** the reader's executed run of 2026-11-15, where one tree ran 8 of its 10 checks
     on a source-built candidate, because its quality gate asks for the invoking runtime's own
     immutable wheel and a source checkout names none by design; this batch changed native gate
     code, and the repairs change the host queue's admission, which every proof on a copy uses.
   - **Considered:** stating that the trees with such gates are proven at their own rebinds on
     the released runtime, after the tag; and a source build of the release head, which leaves
     the same two checks unrun.
   - **Chosen because:** DR-0029 asks for the proof before the tag, and the two gates that a
     source build cannot exercise are where a regression of this batch would hide. A passed full
     proof keeps the archive with its wheel in its lane, so the candidate costs no build, and
     its product tree is the release head's. Fallback, with its date: without a passed run on
     that candidate by 2026-11-20 12:00, the trees with such gates are proven at their own
     rebinds and the weekly page states what stayed unproven.
   - **Applies to:** every readable tree's copy. The reader decides from the diff of the product
     inputs which checks of 2026-11-15 it repeats.
4. **The entry prints the gap codes of the copies run, and the executed proofs are the tag's
   condition.**
   - **Rests on:** DR-0029's sentence that the entry prints the count for each gap code, and its
     rule that no tag is created while a copy shows a new required gap or refusal; the reader's
     preview half of 2026-11-15 over all 13 readable trees.
   - **Considered:** holding this Change until the copies run on its own candidate is read. The
     candidate exists only after this Change's proof, so the entry cannot wait for it.
   - **Chosen because:** the entry prints the counts of the reading of 2026-11-15, made before
     the repairs. A run on the release head's candidate that reads other counts, a new required
     gap or a new refusal stops the tag and returns the release to a lane, where the entry is
     corrected. So an entry under a tag is always the reading of its own head.
   - **Applies to:** the release entry's sentence on the copies run. The tag stays bound to the
     reader's result.
5. **Every Breaking entry names its repair and its order.**
   - **Rests on:** DR-0029's R14; the copies run's preview half, which read
     `generated_projection_drift` in six trees from the artifact retention, repaired by
     `ethos lane project --apply` after the bind and before the proof.
   - **Considered:** leaving the repair to each repository's upgrade notes.
   - **Chosen because:** a new required gap is admitted only when the release ships its repair
     and names it.
   - **Applies to:** the three Breaking entries of this release.
6. **The journey upgrades from 0.2.0-beta.10 alone.**
   - **Rests on:** the reader's count of 2026-11-15 over the 13 readable governed trees: every
     one selects 0.2.0-beta.10 as its runtime, and none selects an older release. Seven declare
     it through the older table form and six declare nothing. Three governed repositories exist
     only on a forge and were not read.
   - **Considered:** the list of the previous release's journey, which also upgraded from two
     alpha releases that subjects selected then; and the releases that trees keep for a rollback
     (0.2.0-beta.9 in seven, three older ones in six), which no tree selects.
   - **Chosen because:** the requirement names the releases that subjects select. A kept rollback
     target is not a selection, and an upgrade leg from a release nobody selects proves a path
     nobody takes.
   - **Applies to:** the journey's predecessor list for this release. The derived set and the
     restore-then-rollback journey are the work of `release-predecessors` and its later row.

## Risks / Trade-offs

- `dev` takes no other landing for the days between this lane and the tag.
- Four repairs enter five days before the tag. Each is small and has its regression; the lane's
  own review, the hosted runs of its head and the copies run on its candidate read them again.
- A defect that the copies run finds on the candidate returns the release to a lane.
