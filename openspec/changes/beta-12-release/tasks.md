# Tasks

## 1. Release entry

- [ ] 1.1 Move the product version to 0.2.0-beta.12. Done when the lane's `ethos --version` reports
      0.2.0-beta.12 and the tests that read the version or the changelog pass.
- [ ] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.12` entry, completed from the landed Changes.
      Done when `changelog_errors` reports nothing with 0.2.0-beta.12 as its release target; the
      entry states each line that design decision 10 lists and no longer says that a
      formatter's refusal is reported alone; it states the law by state without a total and
      the result of the copies run; it names where the known open defects are kept with their
      count at the lane head; and it gives notice that support for Windows ends.
- [ ] 1.3 Record what the release upgrades from. Done when `ethos lane upgrade-from --json`
      passes at the lane head against the committed `[release.upgrade_from]`, the entry names
      the release with that command's counts of subjects and of unread records, and the test
      of ETHOS's own binding fails when the record lacks the previous release.
- [ ] 1.4 Fill the release's fields in the known-defect entries. Done when every entry whose state
      is `closed` holds `fixed_in = "v0.2.0-beta.12"`, no entry holds an empty `since`, no other
      field of any entry differs from `dev`, and a reading of every entry by the reading rules of
      the `known-defect-entries` design names none as malformed.
- [ ] 1.5 Record the task states of `known-defect-entries` and archive it. Done when each of
      its five tasks carries its evidence and its directory stands under
      `openspec/changes/archive/`.

## 2. Acceptance

- [ ] 2.1 Read the lane's diff against `dev` with an independent review. Done when the review
      covers every changed path of the lane and each of its comments has a verdict.
- [ ] 2.2 Pass the pre-check at the lane head: the repository's static checks and every test
      that reads a path the lane changes. Done when none reports a finding on the committed
      head.
- [ ] 2.3 Pass readiness at the lane head. Done when `ethos prove --readiness --execute` passes
      every gate that it runs on the committed head.

## Workflow follow-up

- The reader's pass is repeated on the release head. Each readable tree has a preview equal to its
  earlier one, or a passed full proof, or is named with its reason, by the reader's record. No tag
  is created while a copy shows a new required gap or a new refusal, and the weekly page of the
  tag day states the result.
- The release head is qualified on both Forges before the signed tag. The build, the publication
  and the journey follow by the release guide.
- The release audit is read again before the tag; the tag step compares its unfixed findings with
  the release's recorded list.
- The weekly page's second edition is read from `dev` by a session other than the authors'.
