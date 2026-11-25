# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.12. Done when the lane's `ethos --version` reports
      0.2.0-beta.12 and the tests that read the version or the changelog pass. Evidence: lane
      commit `a103f7525`; the lane reports `ethos 0.2.0-beta.12`; the 109 test files that read a
      path the lane changes passed 1,686 tests, with 1 skipped, at `dacdb7bd4` (2026-11-26,
      05:19:41).
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.12` entry, completed from the landed Changes.
      Done when `changelog_errors` reports nothing with 0.2.0-beta.12 as its release target; the
      entry states each line that design decision 10 lists and no longer says that a
      formatter's refusal is reported alone; it states the law by state without a total and
      the result of the copies run; it names where the known open defects are kept with their
      count at the lane head; and it gives notice that support for Windows ends. Evidence: lane
      commits `a103f7525`, `3066d54e1` and `1f6f7194d`. At `dacdb7bd4`, `changelog_errors` reported
      nothing with 0.2.0-beta.12 as the release target. The entry holds the six items of decision
      10, the three reporting obligations with no total, the copies run's result as the reader
      confirmed it against its receipts, `defects/` with 65 open entries, and the notice under
      `Deprecated`.
- [x] 1.3 Record what the release upgrades from. Done when `ethos lane upgrade-from --json`
      passes at the lane head against the committed `[release.upgrade_from]`, the entry names
      the release with that command's counts of subjects and of unread records, and the test
      of ETHOS's own binding fails in a run with the record taken out. Evidence: lane commit
      `c9f6ea47f`. At `dacdb7bd4` the command passed: the record equals the derived set,
      0.2.0-beta.11 as `attested-main`, from 13 subjects with 3 records unread, as the entry
      prints. With the record taken out of the binding the test failed on the missing release,
      and with the committed version recorded beside it the test failed on the extra name; the
      binding was restored after each run.
- [x] 1.4 Fill the release's fields in the known-defect entries. Done when every entry whose state
      is `closed` holds `fixed_in = "v0.2.0-beta.12"`, no entry holds an empty `since`, no other
      field of any entry differs from `dev`, and a reading of every entry by the reading rules of
      the `known-defect-entries` design names none as malformed. Evidence: lane commit `256562eb1`.
      Against `dev`, nine files under `defects/` differ by one line each: eight `fixed_in` and one
      `since`. A script of the reading rules reads 73 entries at `dacdb7bd4`, 65 open and 8 closed,
      none malformed and none with an empty `since`.
- [x] 1.5 Record the task states of `known-defect-entries` and archive it. Done when each of
      its five tasks carries its evidence and its directory stands under
      `openspec/changes/archive/`. Evidence: lane commit `9a9589c26` records the five task states
      with their evidence, and `8e6059148` archives the Change as
      `openspec/changes/archive/2026-11-25-known-defect-entries`.

## 2. Acceptance

- [x] 2.1 Read the lane's diff against `dev` with an independent review. Done when the review
      covers every changed path of the lane and each of its comments has a verdict. Evidence: a
      first reader read the lane at `c9f6ea47f` and wrote 18 comments, none blocking: 15 were
      repaired, one is carried out by these task states and two stand with their reasons. A
      second reader read the changes up to `c23052b37`, the test among them, and wrote 8
      comments, none blocking: 7 were repaired and one stands with its reason. No reader read
      what followed: the second reader's own repairs, one import that the static pre-check asked
      to be written by the module's path, and the task states and archive of 1.5.
- [x] 2.2 Pass the pre-check at the lane head: the repository's static checks and every test
      that reads a path the lane changes. Done when none reports a finding on the committed
      head. Evidence: at `dacdb7bd4` the pre-check reported no finding (2026-11-26, 05:19:41). A
      first run at `548fe3f44` had found one failing test, which pinned the binding's release
      table; `c23052b37` repaired it.
- [x] 2.3 Pass readiness at the lane head. Done when `ethos prove --readiness --execute` passes
      every gate that it runs on the committed head. Evidence: at `dacdb7bd4` the run passed its
      28 gates, with none failing (2026-11-26, 05:20:46).

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
