# Design

## Context

See the [proposal](proposal.md). The nine gate rows of 0.2.0-beta.12 are archived on `dev` under
passed full proofs, and DR-0029 sets the tag for 2026-11-28. A release is cut from accepted source
by the release guide: a release Change moves the version and curates the entry, lands, and the tag
is created at that accepted head after both Forges qualify it.

## Goals / Non-Goals

Goals:

- One release Change that moves the version, writes the release entry, records what the release
  upgrades from, fills the release's fields in the known-defect entries and records the steps
  that a tag needs.
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
     entry is corrected. So no entry stands under a tag whose own head read otherwise.
   - **Applies to:** the entry's sentence on the copies run.
6. **The release upgrades from 0.2.0-beta.11 alone, and the binding records it.**
   - **Rests on:** the product's own read, `ethos lane upgrade-from`, run in this lane on
     2026-11-26: 13 subjects, every one with 0.2.0-beta.11 selected, 8 of them by a pin on their
     accepted branch and 5 by selection alone, and 3 consumer records that it could not read.
     The reader of the copies run counted 14 trees by its own method, all on 0.2.0-beta.11; the
     two counts were not reconciled tree by tree, and they name the same one release. The
     accepted requirement "A release records what it upgrades from" has the binding record the
     set, and the release guide records it in the release Change.
   - **Considered:** leaving the record to the draft that makes the tag step refuse an empty
     one. The requirement is accepted today, and 0.2.0-beta.11 was tagged without the record.
     Also considered: the releases that trees keep for a rollback, which no subject selects.
   - **Chosen because:** the command derives the set and blocks until the committed binding
     records it, so the record is written from its answer and the command is run again until
     it passes. The selected runtime, 0.2.0-beta.11, reads the key. An upgrade leg from a
     release that nobody selects proves a path that nobody takes, so the journey keeps its one
     predecessor, the previous release.
   - **Applies to:** `[release.upgrade_from]` in `.ethos/release.toml`, the entry's sentence
     on what the release upgrades from, and one test. That test read ETHOS's own binding and
     pinned its release table to the mirror alone, so the record failed it. It now holds
     that the table records the release before the committed one, which every release
     upgrades from: a release Change that moves the version without the record fails the
     test, where 0.2.0-beta.11 was tagged without anyone seeing the gap. The journey takes its
     predecessor from the changelog, as before. The paradigm report checks the record's form;
     no command but the read uses its content in this release.
7. **The entry prints no total of obligations.**
   - **Rests on:** a scan of the product source on 2026-11-26 for the first argument of every
     call that raises a paradigm gap: 48 literal ids and one id for each of the three parameter
     groups, 51 in all, the same at the tag of 0.2.0-beta.11 and at this lane. The previous
     entry printed 47, and its Change states the number without a derivation. No call that
     raises a gap was added or removed since that tag, and the reporting list grew from two
     ids to three.
   - **Considered:** printing 48 as the previous total plus one, which repeats a number that
     cannot be derived; and printing 51 as the total, which is one scan's reading and has no
     enumerator in the product to hold it.
   - **Chosen because:** what a reader acts on is which obligations report and whether any
     was armed, and both are read from the declaration. The entry names the three that
     report, says that none was armed, and says why it prints no total, with the scan's
     count. An enumerator of the obligations is a later Change.
   - **Applies to:** the entry's sentence on the law by state. The same sentence names the
     one act that this release newly refuses as a defect's repair, the deletion of a legacy
     release ref that the hook now protects, so that a reader does not take it for a repair
     without effect. It also places the four gap codes that the code table gained since the
     tag: one names a rename whose apply the previous release already refused, by that
     defect's entry, and three concern only the proof record that cites its plan.
8. **The entry gives notice that support for Windows ends.**
   - **Rests on:** the owner's decision of 2026-11-25 that ETHOS drops Windows in the product,
     its archives and its CI. The removal is prepared and lands after this tag; this release
     still builds and publishes the Windows archives.
   - **Considered:** saying nothing until the release that removes it, which gives a reader on
     Windows no release of notice.
   - **Chosen because:** an entry states what a reader needs before acting, and a new
     adoption on Windows started on this release would lose its platform within weeks. The
     notice names no release for the removal, because none is fixed.
   - **Applies to:** one line under `Deprecated`. The owner can take it out before the tag.
9. **The Change that landed whole is closed here; the six with work left stay open.**
   - **Rests on:** seven Changes stand open on `dev` while the entry states what their landed
     parts do. Six have work left: `format-gates-cost` (the measurement on a governed
     checkout), `unsearchable-path-absence` (the selector that links to itself, and its lane),
     `commit-type-style` (the reading of a governed repository), `gate-reuse` (the owner's
     threshold), `store-retention` (seven tasks) and `proof-output-scratch` (eight tasks). The
     seventh, `known-defect-entries`, landed whole on 2026-11-25 under a passed full proof
     with none of its five tasks recorded.
   - **Considered:** closing `known-defect-entries` in a documentation lane after the tag, as
     first planned. The tree under the tag would then say that none of its work is done.
   - **Chosen because:** decision 1 lets nothing but this lane land before the tag, so this
     lane records that Change's task states from its evidence and archives it. Each entry
     line of the six others states only the part that landed, and their open tasks stay
     where they are.
   - **Applies to:** `openspec/changes/known-defect-entries/` and its archive. No other
     Change is edited.
10. **The entry is completed from a census and from the lane's review.**
    - **Rests on:** a census of 2026-11-26 that held each Change landed since the tag
      against the entry, and the independent review of this lane. The census found two
      Changes that no line stated (the sqlfluff catalog row with the authored-name repair
      text; the shipped Vale and markdownlint files with the known-defect record) and one
      sentence that a later commit had made untrue (a formatter's refusal reported alone).
      The review found two more (the Docs Registry's section on decision records with the
      Writing Standard; the shipped Ruff and format-selection files) and one defect of this
      release that its own bullet did not name (`--grace-days` beside `--release-absent`).
    - **Considered:** stating only what a command or a verdict shows. A shipped policy file
      or governance document that a governed repository's gate or keeper reads is also
      something that repository observes.
    - **Chosen because:** an entry written lane by lane has no reader at its end; the
      release Change is that reader. Each line added says what a governed repository
      observes, and says so when it observes nothing.
    - **Applies to:** the entry's lines that task 1.2 names.

## Risks / Trade-offs

- `dev` takes no other landing for the days between this lane and the tag.
- The release Change is opened two days before the tag. Its diff holds no product code; the
  lane's review, the hosted runs of its head and the reader's pass read it again.
- A defect that the reader's pass finds on the release head returns the release to a lane.
- A reader of the changelog alone no longer sees the known defects' text; the entry sends that
  reader to `defects/` in the repository.
- The record of what the release upgrades from is derived on the releasing host from the
  consumers that its store records. Three records could not be read, so a subject on an
  older release could stand behind one of them unseen.
