# Tasks

## 1. The entry

- [x] 1.1 State the three defects among the known open defects of the 0.2.0-beta.11 entry, each
      with its condition and what to do. Done when `changelog_errors` reports nothing with
      0.2.0-beta.11 as its release target and Prettier and Vale accept the file.
- [x] 1.2 Name, in the entry's sentence on the repaired activation state, the children that the
      repair covers. Done when the sentence names the providers' children and points to
      the known open defects for a declared command.

## 2. Acceptance

- [x] 2.1 Pass the pre-check at the lane head and read the hosted run of that head. Done when both
      pass on the committed head and the difference from `76bae04d3` holds `CHANGELOG.md` and this
      Change's documents alone.

## Workflow follow-up

- The new release head is qualified on both forges, and the release build and its install smoke
  run on the accepted head, before the signed tag.
- The record that closes the copies run names both heads, the difference between them and the
  owner's decision.
