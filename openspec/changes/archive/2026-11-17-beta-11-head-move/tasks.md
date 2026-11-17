# Tasks

## 1. The reader of a consumer's state

- [x] 1.1 Add the cases of the reader: a consumer whose selectors, or whose parent, lie below a
      directory that may not be searched; a consumer whose path is gone, or is a link that
      names nothing or a file; a file where its state directory stood; and a record of a path
      that no host can be asked about. Done when the closed directory, the link, the file and
      the damaged record each fail without 1.2.
      (Run with each earlier form of the reader in the lane's tree. At the release head on
      2026-11-17 the closed directory fails under Python 3.14 in two states. On 2026-11-18 the
      link, the file and the closed parent fail under the release head's reading of the path,
      and the damaged record fails before `d32673c8b`.)
- [x] 1.2 Ask the host for a selector's own status in `named_runtime`, and for the consumer
      path's status in the reader of a consumer's state. Done when the module passes on Python
      3.12, 3.13 and 3.14, the tests of the selector's other callers pass, and the guards on
      owned literals and decision density pass.
      (At `8e624f79d` the module and its two neighbours pass on Python 3.12, 3.13 and 3.14, 47
      cases on each; the tests of the selector's other callers and the four guards pass on Python
      3.14.)

## 2. The entry

- [x] 2.1 Move each note of the Unreleased section under the heading of its kind in the entry
      of 0.2.0-beta.11. Done when the Unreleased section holds no note and the changelog check
      reports nothing with 0.2.0-beta.11 as its release target.
      (`changelog_errors` with the target 0.2.0-beta.11 reports nothing at `9479505e9`.)
- [x] 2.2 Read each of the entry's twelve known open defects against the lane head. Done when
      each one that a row repairs has left the list with that row named here, and each one that
      stays is confirmed open at the lane head.
      (Three left the list: the temporary directory inside a work tree and a patch line that
      begins like a file line, by `postimage-workspace`, and the host queue that cannot be
      opened, by `host-reservation-guests`. A probe refuses the second at the release head and
      admits it at the lane head, on both targets. Nine stay: the audit at the lane head
      reports the two bundled findings, and the code behind the other seven is as at the
      release head or keeps the stated reading.)
- [x] 2.3 Amend the Fixed item on vendored and generated paths with the sources that count, and
      add the Fixed item for the reader of a consumer's state. Done when the prose gate accepts
      the entry.
      (Readiness at `9479505e9`: 28 gates pass, the prose gate among them.)
- [x] 2.4 State in the design how the batch's name in the records maps to the release that
      ships it. Done when decision 6 holds the sentence.
- [x] 2.5 Name the accepted advisory and its three copies among the entry's known open
      defects, and the hosts of the release journey as the batch leaves them. Done when the
      entry names every advisory that the audit at the lane head reports.
      (The audit at the lane head reports GHSA-3g3m-2fjr-6pw4, GHSA-g3hv-75wg-m249 and
      GHSA-fc5q-39xc-vjpf, the last with one approval.)
- [x] 2.6 State what the reading of this release's candidate on the copies of the governed
      repositories found. Done when the entry's sentence holds the counts of a reading of this
      head's product tree.
      (Read on 2026-11-18 on a candidate built from `d32673c8b`, whose product tree is the lane
      head's: 13 repositories; `generated_projection_drift`, 14, in 7; every other code 0; no
      new refusal. The entry holds it at `9479505e9`.)

## 3. The standing rule

- [x] 3.1 Show the owner the rule's sentence for the release guide. Done when a page shows the
      sentence as an ask; a workflow follow-up carries its tracking.
      (The release lead's page of 2026-11-18 on the two repairs shows the sentence as its third
      ask.)

## 4. Lane and release

- [x] 4.1 Read by a preview whether a landing admits the lane's Changes whose tasks are open.
      Done when the preview's answer is recorded here and, on a refusal, those Changes are
      drafts again.
      (At `f8f00f8e1` the landing's preview names one gap, `proof_not_proven`.)
- [x] 4.2 Pass the model review of the lane's code since the reviewed head, the precheck and
      readiness at the lane head. Done when each passes on the committed head.
      (Five model reviews of the code since `4a5029e96`, 38 comments, each with a verdict; the
      last product commit is `d32673c8b`, and the fifth review's two comments on tests are in
      `c6a9c31cc`. The precheck and readiness pass at `9479505e9`.)

## 5. The accepted advisory

- [x] 5.1 Record the owner's acceptance as one disposition bound to this repository's lock. Done
      when the audit at the lane head passes with one approval and a test holds the record's
      digest against the committed lock.
      (`0578ead53`, `65d611ce9` and `d32673c8b`; the audit at `d32673c8b` passes with one
      approval and four reported findings.)

## Workflow follow-up

- The full proof of the archived head passes, or the way back of the design's decision 2 is
  taken at 2026-11-19 12:00.
- The copies run of DR-0029 runs on the candidate that the proof kept, and its reader's record
  is read before the page of 2026-11-20.
- The landed head is published to both forges and qualified on both. The release build with its
  install smoke and the launchd dry run are read at that head before the page of 2026-11-20.
- The release run's journey is read on its three hosts, the Linux arm64 leg for the first time.
  The entry names a host whose journey failed or was unavailable.
- After the journey passes, the release is accepted on the releasing host, and the apply reads
  `accepted` and a second run `unchanged`: the follow-up of `release-acceptance`.
- The standing rule's sentence is tracked as the owner answers it, in a Change of its own, or
  withdrawn.
- The gap of the audit's rule, a finding whose advisory also names the registry's latest
  release, goes to the committee as a draft with the measurement of 2026-11-18.
