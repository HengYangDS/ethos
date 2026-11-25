# Design

## Context

See the [proposal](proposal.md). The nine gate rows of 0.2.0-beta.12 are archived on `dev` under
passed full proofs, and DR-0029 sets the tag for 2026-11-28. A release is cut from accepted source
by the release guide: a release Change moves the version and curates the entry, lands, and the tag
is created at that accepted head after both Forges qualify it.

## Goals / Non-Goals

Goals:

- One release Change that moves the version, writes the release entry, fills the release's fields
  in the known-defect entries and records the steps that a tag needs.
- The reader's pass on the release head before the tag, or each tree it could not read named with
  its reason.

Non-Goals:

- Any gate row, and any product code. The rows of 0.2.0-beta.13 land after the tag.
- The command that reads `defects/`, and the check that names a malformed entry. Both are later
  Changes of the known-defect carrier.
- The weekly page's commands. A value read by hand is marked so.

## Decisions

1. **The release head is the last landing before the tag.**
   - **Rests on:** the release guide, whose tag is created at the accepted head that the release
     Change landed; DR-0029's rule that the candidate is proved on a copy of every readable tree
     before the tag.
   - **Considered:** landing prepared rows of 0.2.0-beta.13 before the tag, which would put them
     into this release without a copies run on their head.
   - **Chosen because:** the copies run stands for one head, and a new product change starts it
     again. Accepted: nothing but this lane lands on `dev` before the tag.
   - **Applies to:** `dev` from this lane's landing to the tag. Work in lanes and proposal refs
     continues.
2. **The entry names where the known open defects are kept; it does not copy them.**
   - **Rests on:** the owner's decision of 2026-11-19 that the known-defect record is a carrier
     inside the repository, and the design of `known-defect-entries`, which landed 73 entries
     under `defects/` and gives the release's Change the fields it fills. The previous entry
     carried ten defects as prose, while more than thirty others known before its tag were not
     in it.
   - **Considered:** copying the titles of the open entries into the entry, which restores the
     hand-kept list that the carrier replaces; and generating that list by a script of this lane,
     which the read command of a later Change makes unnecessary.
   - **Chosen because:** one fact has one source. The entry states the count of open entries at
     its head and names the directory; each entry file states since which release the defect is
     there and how to work around it. The entry also states one defect in words, because the owner
     decided on 2026-11-18 that this release's entry states it: the product design contract says
     that a repository maps its branch names, and the product fixes them.
   - **Applies to:** the entry's sentence on known open defects, in this release and after it. The
     entry claims no class for the open defects; the previous entry's "none in a blocking class"
     was a reading of twelve items and is not repeated over 65.
3. **The release's fields in `defects/` name a tag that this Change does not create.**
   - **Rests on:** the entries' design: the Change that writes a release's entry fills `fixed_in`
     for the entries closed since the previous tag, and fills an empty `since` when the defect
     ships first with this release.
   - **Considered:** filling the fields in the first lane after the tag, when the tag resolves.
     The released tree would then say of eight repaired defects that no release carries the
     repair.
   - **Chosen because:** the tag is created at this lane's landed head or not at all. If the tag
     is not created there, the release returns to a lane, which corrects these fields with the
     entry's date.
   - **Applies to:** nine files under `defects/`. No other field of any entry changes.
4. **The reader reads the release head by its rule for a landing without product code, and proves
   in full where a preview differs.**
   - **Rests on:** the reader's executed proofs on the candidate built at the last product
     change: twelve governed repositories passed in full, one is refused before execution on two
     gaps of its own tree that the previous release reads the same, and one without an accepted
     branch is evidence only. After the known-defect entries landed, the reader's previews of all
     fourteen equalled those before it in verdict, gaps, gate count, audit, lifecycle, scope
     binding and plan digest. This lane changes the version, the changelog and nine entry files.
   - **Considered:** a full executed round on the release head, about three to four hours of the
     shared host's one queue for a tree whose product code the proved candidate already holds;
     and no further reading, which leaves the moved version unread on every tree.
   - **Chosen because:** the version is the one product input that this lane moves, and a
     preview on each copy reads it through the selection, the audit and the plan. A preview that
     differs in a gate, a gap or a plan step is followed by a full proof of that tree under its
     own ticket, and a new required gap or a new refusal stops the tag.
   - **Applies to:** every readable tree's copy at the release head. The reader records each
     receipt; the release lead closes the copies run for the head from that record.
5. **The entry prints the result of the copies run, and the reader's pass is the tag's
   condition.**
   - **Rests on:** DR-0029's sentence that the entry prints the count for each gap code, and its
     rule that no tag is created while a copy shows a new required gap or refusal.
   - **Considered:** holding this Change until the release head is read. The head exists only
     after this Change lands, so the entry cannot wait for it.
   - **Chosen because:** the entry prints the reading made before this lane. A pass on the
     release head that reads otherwise stops the tag and returns the release to a lane, where the
     entry is corrected. So an entry under a tag is always the reading of its own head.
   - **Applies to:** the entry's sentence on the copies run.
6. **The journey upgrades from 0.2.0-beta.11 alone.**
   - **Rests on:** the reader's count of 2026-11-26 over the fourteen trees: every one selects
     0.2.0-beta.11 as its runtime. Eleven pin it in their toolchain declaration and three select
     it through the runtime their repository holds.
   - **Considered:** the releases that trees keep for a rollback, which no tree selects.
   - **Chosen because:** the requirement names the releases that subjects select, and an upgrade
     leg from a release nobody selects proves a path nobody takes.
   - **Applies to:** the journey's predecessor list for this release.

## Risks / Trade-offs

- `dev` takes no other landing for the days between this lane and the tag.
- The release Change is opened two days before the tag. Its diff holds no product code; the
  lane's review, the hosted runs of its head and the reader's pass read it again.
- A defect that the reader's pass finds on the release head returns the release to a lane.
- A reader of the changelog alone no longer sees the known defects' text; the entry sends that
  reader to `defects/` in the source tree.
