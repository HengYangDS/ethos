# Design

## Context

See the [proposal](proposal.md). The release head of 0.2.0-beta.11 was frozen on 2026-11-16.
Since then seven defects were measured at it, then a regression of the release itself, then two
older defects of one reader. The owner's three answers of 2026-11-17 took the plan from the
entry alone, to the entry and one repair, to the whole reviewed batch with the repairs. This
Change is the move's own: it carries the reader's repair and the release entry, and it names
the order in which the lane reaches the tag. The regression's repair is
`authored-selection-local-attributes`.

## Goals / Non-Goals

Goals:

- 0.2.0-beta.11 ships the batch's repairs instead of listing the defects they repair.
- The host store keeps an installation whose consumer it cannot read.
- The entry states what the release holds, and lists only defects that are open at its head.

Non-Goals:

- A change of the tag day, of a line of the gate, or of the release's name.
- The other readers that ask a path question which differs by interpreter; they belong to
  `unsearchable-path-absence`.
- The prepared rows of 0.2.0-beta.13, whose Changes in this lane stay open and unbuilt.

## Decisions

1. **The move carries the batch.**
   - **Rests on:** the seven defects of the proposal, each confirmed at the release head and each
     repaired by a reviewed row of the batch; the batch green on both forges at its code head;
     and the release chain, which runs once for any move of the head.
   - **Considered:** the entry alone, the owner's first answer, which ships seven known defects
     beside their finished repairs; the entry and the regression's repair, the second answer.
   - **Chosen because:** the owner decided it on 2026-11-17, on a page that set the three ways
     beside each other. A found defect whose repair is reviewed is repaired, and the order of
     the batches was the only reason against it.
   - **Applies to:** the lane of the batch, which becomes the lane of the release head.
2. **The way back has an hour.**
   - **Rests on:** the last chain of the release head, about 5.5 hours from the proof to the
     launchd dry run, and the page of 2026-11-20 that asks the owner for the tag.
   - **Considered:** no way back, which stakes the tag day on one proof in a shared host queue.
   - **Chosen because:** the release lead bound it on the owner's page. If the batch's whole
     verification has not passed by 2026-11-19 12:00, a lane from the accepted branch carries
     the entry's seven items and the regression's repair alone, and the batch lands after the
     tag.
   - **Applies to:** this lane's order of work; the regression's repair is kept in a form that
     applies to the release head for that case.
3. **A selector that cannot be looked at reads `unknown`.**
   - **Rests on:** a case with a recorded consumer in three states of a directory that may not
     be searched. At the release head under Python 3.14 the cleanup deletes the installation
     when the Git common directory or the directory of the selectors is closed; under 3.12 and
     3.13 it keeps it. The reader asks whether the selector exists, and Python 3.14 answers no
     where the older interpreters raise.
   - **Considered:** changing the selector's reader itself, which rollback and the exit also
     call and whose answers there are not classified; reading such a consumer as `absent`,
     which the plan of legacy supply releases.
   - **Chosen because:** the accepted requirement says that unknown liveness prevents deletion.
     The reader asks the host for the selector's own status first, which raises there on every
     interpreter, and creates, locks and writes nothing.
   - **Applies to:** the reader of a consumer's state in the host store's retention. A second
     reader tried to refute it on three interpreters and did not.
4. **A consumer whose path is a link that names nothing reads `unknown`.**
   - **Rests on:** the second reader's probe and a case that fails at the release head on every
     interpreter: the reader excepted a link from "the path is gone", read on, found no
     selector and answered `released`, and the cleanup removed the record and the installation.
   - **Considered:** `absent`, as a path that is gone. The accepted quality specification says
     that a dangling root link is not a genuinely absent consumer directory, and the plan of
     legacy supply does not hold an installation for an absent consumer.
   - **Chosen because:** nothing says what the link named, so its liveness is unknown, and
     unknown keeps the record and the installation in both plans.
   - **Applies to:** the same reader. Found under the owner's standing rule for a repair of one
     reader that adds no refusal.
5. **No requirement's words change.**
   - **Rests on:** the accepted requirement "Installed product migration preserves live
     consumers", which states that unknown liveness prevents deletion.
   - **Considered:** a scenario for each of the two states.
   - **Chosen because:** the reader did not do what the requirement already says. The cases
     hold the two states; a scenario would restate the sentence. So `skip_specs` applies.
   - **Applies to:** this Change's artifacts.
6. **The entry is written from the batch's notes, and its list is read again.**
   - **Rests on:** the lane's changelog, whose Unreleased section holds the batch's notes above
     the entry of 0.2.0-beta.11, and that entry's twelve known open defects.
   - **Considered:** a second entry for the batch, which would name a release that does not
     exist.
   - **Chosen because:** one release has one entry. Each note moves under the entry's heading
     of its kind. Each listed defect is read against the lane head and leaves the list when a
     row repairs it, with the row named in the task's evidence.
   - **Applies to:** `CHANGELOG.md`, and every tracked text of the lane that names
     0.2.0-beta.12 as the batch's release.
7. **The standing rule is shown before it is tracked.**
   - **Rests on:** the owner's answer of 2026-11-17 and its four conditions, in the proposal.
   - **Considered:** writing it into the release guide with this Change.
   - **Chosen because:** the owner approved the rule on a page of asks and has not seen its
     sentence in the page that would hold it. The lead shows the sentence first.
   - **Applies to:** `docs/guides/release-and-publication.md`, in a later commit of this Change
     or in its own.

## Risks / Trade-offs

- [The batch's proof does not pass in time] -> decision 2. The regression's repair and the
  entry's seven items are kept ready for the release head as it is.
- [A release head with Changes whose tasks are open] -> the lane holds six Changes of
  0.2.0-beta.13 with documents and no code. Whether a landing or a release admits them is read
  by a preview before the proof; if not, they return to drafts in one commit.
- [Left in the reader] -> under Python 3.12 and 3.13 a consumer whose parent may not be
  searched ends the whole cleanup with an error, and under 3.12 so does a selector that names a
  local runtime which links to itself. Both are older than this release, lose nothing, and are
  named in `unsearchable-path-absence`.
- [Windows] -> both cases skip there; a directory that its owner cannot search needs POSIX
  modes. The hosted Windows legs run the rest of the module.
- [The repairs' reviews] -> the first repair has a second reader; the second has the lead
  alone until the batch's model review reads the lane's code.
