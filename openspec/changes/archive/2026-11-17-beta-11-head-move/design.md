# Design

## Context

See the [proposal](proposal.md). The release head of 0.2.0-beta.11 was frozen on 2026-11-16.
Since then seven defects were measured at it, then a regression of the release itself, then
older defects of one reader, and on 2026-11-17 an advisory without a fix began to block every
proof. The owner's three answers of 2026-11-17 took the plan from the
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
     launchd dry run for a head whose change was the entry alone; the copies run of DR-0029,
     which a head with product code owes again and which took about ten host hours the last
     time; and the page of 2026-11-20 that asks the owner for the tag.
   - **Considered:** no way back, which stakes the tag day on one proof in a shared host queue.
   - **Chosen because:** the release lead bound it on the owner's page. If the batch's whole
     verification has not passed by 2026-11-19 12:00, a lane from the accepted branch carries
     the entry's seven items and the regression's repair alone, and the batch lands after the
     tag.
   - **Applies to:** this lane's order of work. For that case the regression's repair is
     applied to the release head from this lane's commits, which was not tried since the
     repair took its last form.
3. **The selector's one reader asks the host for the selector's status.**
   - **Rests on:** a case with a recorded consumer in three states of a directory that may not
     be searched. At the release head under Python 3.14 the cleanup deletes the installation
     when the Git common directory or the directory of the selectors is closed; under 3.12 and
     3.13 it keeps it. The selector's reader, `named_runtime`, asks whether the selector
     exists, and Python 3.14 answers no where the older interpreters raise.
   - **Considered:** a helper in the host store's reader that asks for the selector's status
     before it calls the selector's reader. The first form of this repair did that; a model
     review named it a second owner of the selector's path, and it left the three other callers
     with the wrong answer under Python 3.14. Raising for a selector below a file as well, which
     the second form did: POSIX then kept an installation that Windows released, because
     Windows reports such a path as not found.
   - **Chosen because:** one behavior has one owner. `named_runtime` asks the host for the
     selector's own status, which raises on every interpreter for a place that may not be
     looked at. It answers that no selector is there where the host says so: the file is
     missing, or a file stands where one of its directories was, as every release answered on
     every host. Each of its four callers already reads an error as "not read": the host store
     keeps the installation, the rollback guidance and the rollback's release do nothing, and
     the upgrade reading answers unread. The accepted requirement says that unknown liveness
     prevents deletion.
   - **Applies to:** `named_runtime` and so its four callers. A second reader tried to refute
     the first form on three interpreters and did not.
4. **The reader asks the host for the consumer path's status, and what is no directory reads
   `unknown`.**
   - **Rests on:** cases that fail at the release head. A link that names nothing: the reader
     excepted a link from "the path is gone", read on, found no selector and answered
     `released`, on every interpreter. A file at the path, which Git leaves when it moves its
     directory: the same. Each time the cleanup removed the record and the installation. A
     consumer below a directory that may not be searched: the path questions raise under
     Python 3.12 and 3.13, which ended the whole cleanup, and answer no under 3.14, which read
     the consumer as absent. A second reader found the first, and model reviews the others.
   - **Considered:** `absent` for each, as a path that is gone. The accepted quality
     specification says that a dangling root link is not a genuinely absent consumer directory,
     and the plan of legacy supply does not hold an installation for an absent consumer.
   - **Chosen because:** a link that names nothing, a file, and a place that cannot be looked
     at do not say what stands there, so the liveness is unknown, and unknown keeps the record
     and the installation in both plans. The host's status is asked once, so the answer is the
     same on every interpreter. A record of a path that no host can be asked about, such as one
     with a null character, reads `unknown` as well.
   - **Applies to:** the host store's reader of a consumer's state. Repaired under the owner's
     standing rule. With decision 3 the repair changes two readers, which the release lead
     reports to the owner on the page after it.
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
   - **Applies to:** `CHANGELOG.md`. The batch keeps the name that its records gave it: "the
     batch of 0.2.0-beta.12" in DR-0028, DR-0029 and the Changes is the batch that
     0.2.0-beta.11 ships, and those records are not edited. The release after this one keeps
     its number, 0.2.0-beta.12, and carries the batch that they call the batch of
     0.2.0-beta.13.
7. **The standing rule is shown before it is tracked.**
   - **Rests on:** the owner's answer of 2026-11-17 and its four conditions, in the proposal.
   - **Considered:** writing it into the release guide with this Change.
   - **Chosen because:** the owner approved the rule on a page of asks and has not seen its
     sentence in the page that would hold it. The lead shows the sentence first.
   - **Applies to:** `docs/guides/release-and-publication.md`, in a Change of its own after
     the owner's answer; a workflow follow-up of this Change carries it.
8. **One advisory is accepted for one artifact of this repository's lock.**
   - **Rests on:** GHSA-fc5q-39xc-vjpf, which since 2026-11-17 names every picomatch release
     through 4.0.7 and has no fixed release. The lock holds three copies. The audit reports the
     two whose owning release is its registry's latest, and blocks picomatch 2.3.2, which
     markdownlint-cli2 0.24.1 reaches through micromatch 4.0.8: each is its registry's latest,
     and micromatch accepts the 2.x line alone, so no upgrade removes it. The accepted
     requirement "Findings without a stable upstream fix do not block" lets a finding behind
     its registry's latest block until it is upgraded or an exact disposition applies.
   - **Considered:** changing the rule, so that a finding whose advisory also names the
     registry's latest release reports: that changes an accepted scenario of a security gate,
     and goes to the committee as a draft with this measurement. Waiting for a fixed release,
     which gives the tag no day.
   - **Chosen because:** the owner accepted the risk on 2026-11-18, on a page that showed the
     advisory, the three copies and both ways: this artifact, in this repository's lock, until
     2026-12-02. The record names the lock's digest. The product ships its audit policy, and
     the audit of a governed repository adds the product's records to its own, so a record
     without the lock would accept the artifact in every repository's lock, which nobody
     approved. A change of the lock ends the match until the record is read again, and a test
     holds the digest against the committed lock.
   - **Applies to:** `.config/checks/dependency-vulnerabilities/policy.toml`, and the entry's
     known open defects, which name the advisory and its three copies.

## Risks / Trade-offs

- [The batch's proof does not pass in time] -> decision 2. The regression's repair and the
  entry's seven items are kept ready for the release head as it is.
- [A release head with Changes whose tasks are open] -> the lane holds six Changes of
  0.2.0-beta.13 with documents and no code. The landing's preview at the lane head names one
  gap, the proof that is not yet made, and the accepted branch has carried an open Change with
  an unticked task through three landings and a release preview.
- [Left in the reader] -> under Python 3.12 a selector that names a local runtime which links
  to itself ends the whole cleanup with an error. It is older than this release, loses
  nothing, and is named in `unsearchable-path-absence`. On Windows a junction that names
  nothing is still listed as absent, as before; its installation is kept either way. A file
  where a consumer's state directory stood selects nothing, as in every release, so the moment
  in which Git replaces a common directory by a file between the reader's two questions is
  not closed.
- [A kept consumer is not named] -> the cleanup's report lists a consumer only when it is
  absent. One that reads `unknown` keeps its installation and appears under no name, so its
  owner cannot see which path holds the bytes. The report's shape belongs to
  `store-retention`, whose tasks carry it.
- [Windows] -> both cases skip there; a directory that its owner cannot search needs POSIX
  modes. The hosted Windows legs run the rest of the module.
- [The repairs' reviews] -> a second reader and five model reviews read the repairs. Each of
  the first four found a state that a case then showed, and each is repaired. A state that no
  review named may remain; in each such state the reader keeps the installation or raises.
- [The accepted advisory] -> a pattern in a governed repository's own lint configuration can
  make its Markdown lint gate slow. The gate runs as a local command and serves no request,
  and its bound ends it.
