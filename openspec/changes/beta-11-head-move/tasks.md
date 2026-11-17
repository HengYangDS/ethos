# Tasks

## 1. The reader of a consumer's state

- [ ] 1.1 Add the case for a consumer whose selectors lie below a directory that may not be
      searched, in three states, and the case for a consumer whose path is a link that names
      nothing. Done when, without 1.2, the first fails under Python 3.14 in two states and the
      second fails under Python 3.14 and 3.12.
- [ ] 1.2 Ask the host for a selector's own status before it is read, and answer `unknown` for
      a consumer whose path is a link that names nothing. Done when the module passes on Python
      3.12, 3.13 and 3.14 and the guards on owned literals and decision density pass.

## 2. The entry

- [ ] 2.1 Move each note of the Unreleased section under the heading of its kind in the entry
      of 0.2.0-beta.11. Done when the Unreleased section holds no note and the changelog check
      reports nothing with 0.2.0-beta.11 as its release target.
- [ ] 2.2 Read each of the entry's twelve known open defects against the lane head. Done when
      each one that a row repairs has left the list with that row named here, and each one that
      stays is confirmed open at the lane head.
- [ ] 2.3 Amend the Fixed item on vendored and generated paths with the sources that count, and
      add the Fixed item for the reader of a consumer's state. Done when the prose gate accepts
      the entry.
- [ ] 2.4 Correct each tracked text of the lane, outside the archive, that names 0.2.0-beta.12
      as the batch's release. Done when a search finds the name only where a text speaks of the
      release after this one.

## 3. The standing rule

- [ ] 3.1 Show the owner the rule's sentence in the release guide. Done when the owner has
      answered on a page and the sentence is tracked as answered or withdrawn.

## 4. Lane and release

- [ ] 4.1 Read by a preview whether a landing admits the lane's Changes whose tasks are open.
      Done when the preview's answer is recorded here and, on a refusal, those Changes are
      drafts again.
- [ ] 4.2 Pass the model review of the lane's code since the reviewed head, the precheck and
      readiness at the lane head. Done when each passes on the committed head.
- [ ] 4.3 Pass the full proof at the archived head, or take the way back of the design's
      decision 2 at 2026-11-19 12:00. Done when the proof's result or the way back is recorded
      here with its time.
- [ ] 4.4 Land, publish to both forges and run the release chain at the new head: both
      qualifications, the release build with its install smoke, the copies run and the launchd
      dry run. Done when each result is read at the new head before the page of 2026-11-20.
