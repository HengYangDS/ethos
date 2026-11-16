# Tasks

## 1. The set, the classes and the carrier

- [x] 1.1 Add the pure module `ethos.repository.release.predecessors`: the subject, the support
      window, the derivation and the carrier's reader. Done when
      `tests/unit/release/test_predecessors.py` shows the previous release alone, a pinned and a
      selected older release, a subject at the window's edge and one a day outside it, the release
      itself, a subject by its selection alone, a version that the changelog does not list, the
      count of subjects for each named version, a release without its entry, and each form of the
      carrier with the three that refuse.
- [x] 1.2 Name the changelog's released entries through its own parser, and spell one exact
      release through the pin module. Done when the same module's first test reads the entries
      newest first and the carrier refuses an inexact version.
- [x] 1.3 Admit `upgrade_from` to the release table's key set. Done when the paradigm repair
      deletes an unread key beside a recorded table and keeps the table, and the case fails
      without the key.
- [x] 1.4 Report a record that its reader refuses under `release-binding`, and never delete it.
      Done when a record that is no table, misnames a release or gives another class is
      reported at `release.upgrade_from` and the repair plans no edit.
- [x] 1.5 Refuse a changelog whose history is out of order or names a release twice. Done when
      `released_versions` raises the history's own errors for both.

## 2. The derivation

- [x] 2.1 Read the subjects from the host store's consumer records. Done when one regression over
      fixture repositories shows a pin moved back to a release whose name begins another's, the
      older form at the window's edge, a subject a day outside the window, a subject by its
      selection alone with no time, a subject whose pin and selection differ, three declared pins
      that cannot be read, each counted by itself with its repository a subject by its selection,
      a repository with neither, a repository that is gone, a torn record, the releasing
      repository left out, and rows ordered by bump against the order of their paths.
- [x] 2.2 Add the catalog operation `lane.upgrade-from` with its three registered gaps. Done when
      the operation's regression shows an undeclared, an empty, an incomplete and a complete
      record, a record with another class, a development build named as unlisted without a
      refusal, the counts by pin form and by selection, a host without a store derives the
      previous release alone, and the catalog test counts one more operation.
- [x] 2.3 Count what cannot be read and never read it as absent. Done when two torn records
      count twice, an installation that records no consumer is counted by itself, a
      repository whose accepted branch cannot be read is unread, and a selection that cannot
      be read is counted while its repository stays a subject by its pin.
- [x] 2.4 Carry registered gaps and their own repairs in a refusal. Done when a gap outside the
      record does not ask for the record, and an operating system error is named without its
      message or a path.
- [x] 2.5 Derive beside a record that its reader refuses, block on a refusal that carries no
      gap, and read an installation directory that is a link once. Done when the case of
      another class carries the derived releases, a refusal without a gap blocks under its
      class's name, a linked installation's consumer is a subject, a link beside its target
      is counted once, and a link whose target is gone is counted.

## 3. Documents

- [x] 3.1 State the derivation, the record and the waiver in the release guide, and add the
      changelog entry. Done when Prettier, the prose gate and the documentation registry report
      nothing on both files.
- [x] 3.2 Add the decision record DR-0030 for the candidate's subject set and the waiver, with
      its entry in the decisions index. Done when the documentation registry, Prettier and the
      prose gate report nothing on both files, and the record names no repository and fixes no
      number of subjects.

## 4. Acceptance

- [ ] 4.1 Pass the focused gates on the lane head: the test modules that import a changed module,
      Ruff, ty, import-linter, `openspec validate release-predecessors --strict` and Prettier. Done
      when each reports no finding.
- [x] 4.2 Measure the source budget against the lane base. Done when the three measured figures
      are recorded in this task.

## 5. Lane, hosted and owner tasks

- [x] 5.1 Lane: run `ethos lane upgrade-from --json` on the releasing host with a runtime that
      contains this Change. Done when a session other than the author's has read the rows, and each
      unread record and each subject outside the window is explained. Evidence: the read at
      `66770b394` lists 13 subjects, none unread and none outside the window; the governing session
      read each row against the tree's accepted head, which is the local accepted branch.
- [ ] 5.2 Hand the record of `[release.upgrade_from]` in the product's own release binding to the
      first release Change whose selected runtime contains this Change. Done when the Workflow
      follow-up names it: that lane records the table, the operation passes on its committed head,
      and the predecessor's paradigm audit does not report the table.
- [ ] 5.3 Hand the journey's dispatch input to the release that first records the table. Done when
      the Workflow follow-up names it: the dispatch names every recorded release in
      `journey_previous`, and each leg's receipt names every recorded release as a predecessor.
- [x] 5.4 Owner: read the text of DR-0030, which the release lead shows before this row lands.
      Done when the owner has accepted the text, or the record carries the owner's corrections.
- [ ] 5.5 Lane: read the weekly page's measure of pins in by DR-0030's set. Done when its total is
      the count of the operation's rows inside the window, without the waived repository and without
      the repositories of the two families under repair, which the page names by shape.

## Workflow follow-up

- `release-predecessors-binding`: `land --release` re-derives the record offline and refuses an
  empty or incomplete one, only for a release binding that declares the table. Read again at
  the cut of 0.2.0-beta.13.
- `upgrade-path-status`: `status` names, for a governed repository outside the support window,
  the newest release with a qualified path. Read again at the cut of 0.2.0-beta.14.
- Release: the first release Change whose selected runtime contains this Change records
  `[release.upgrade_from]` in the product's own release binding, with the releases that
  `ethos lane upgrade-from --json` derives; the operation passes on that lane's committed head, and
  the predecessor's paradigm audit does not report the table.
- Release: for the release that first records `[release.upgrade_from]`, name every recorded release
  in the journey's dispatch input `journey_previous`, and read in each leg's receipt that it names
  every recorded release as a predecessor.
