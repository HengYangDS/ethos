# Tasks

## 1. Release entry

- [ ] 1.1 Move the product version to 0.2.0-beta.12. Done when the lane's `ethos --version` reports
      0.2.0-beta.12 and the tests that read the version or the changelog pass.
- [ ] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.12` entry, completed from the landed Changes.
      Done when `changelog_errors` reports nothing with 0.2.0-beta.12 as its release target, each
      line that the reader's census of 2026-11-26 names as absent or partial is stated, the entry
      states the law by state and the result of the copies run, and it names where the known open
      defects are kept with their count at the lane head.
- [ ] 1.3 Name the release that the journey upgrades from. Done when the entry names the release
      that the readable trees select, by the reader's count, and the design records the count.
- [ ] 1.4 Fill the release's fields in the known-defect entries. Done when every entry whose state
      is `closed` holds `fixed_in = "v0.2.0-beta.12"`, no entry holds an empty `since`, no other
      field of any entry differs from `dev`, and a reading of every entry by the design's reading
      rules names none as malformed.

## 2. Acceptance

- [ ] 2.1 Read the lane's diff against `dev` with an independent review. Done when the review
      covers every changed path of the lane and each of its comments has a verdict.
- [ ] 2.2 Pass the precheck at the lane head. Done when it reports no finding on the committed
      head.
- [ ] 2.3 Pass readiness at the lane head. Done when every gate it runs passes on the committed
      head.

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
