# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.11. Done when the lane's `ethos --version` reports
      0.2.0-beta.11 and the tests that read the version or the changelog pass. Evidence: lane commit
      `da63d1e11`; the lane reports `ethos 0.2.0-beta.11`, and the 40 test modules that read the
      version or the changelog passed 849 tests at 02:43:40.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.11` entry, completed from the landed Changes,
      this lane's repairs and the release build's audit. Done when `changelog_errors` reports
      nothing with 0.2.0-beta.11 as its release target, each Breaking entry names its repair and its
      order, the entry prints the count for each gap code of the copies run and the law by state,
      and it names every advisory that the audit reports. Evidence: lane commit `da63d1e11`.
      `changelog_errors` reported nothing with 0.2.0-beta.11 as the release target. The dependency
      audit of the production-release scope at `98d12d438` decided pass at 01:01:31 with no
      unapproved subject and reported two advisories as unfixed upstream, GHSA-3g3m-2fjr-6pw4 and
      GHSA-g3hv-75wg-m249, in npm 12.2.2's bundled glob 13.0.6 and minimatch 10.2.5; the entry names
      both. The lane changes none of the audit's seven inputs, the gate `dependency-vulnerabilities`
      passed at `da63d1e11` in the readiness run, and the audit is read again before the tag. The
      entry states 47 obligations, 45 that refuse and 2 that report, the count for each gap code of
      the copies run of 2026-11-15, and a repair with its order in each of the three Breaking
      entries.
- [x] 1.3 Name the release that the journey upgrades from. Done when the entry names the release
      that the readable trees select, by the reader's count, and the design records the count.
      Evidence: the entry and design decision 6 name 0.2.0-beta.10, which 13 of 13 readable trees
      select by the reader's count of 2026-11-15.

## 2. Acceptance

- [x] 2.1 Read the lane's diff against `dev` with the model review. Done when the review covers
      every changed code path of the lane and each of its comments has a verdict. Evidence: three
      parts cover the lane's code from `98d12d438` to `ec33ac087`, 11, 11 and 14 files, each
      complete, with 5, 2 and 3 comments. Seven comments were repaired in the lane and three are
      carried by drafts; no code changed after `ec33ac087`.
- [x] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: at `da63d1e11` the static precheck passed with no finding at 02:24:07, and
      readiness passed 28 gates with none failing at 03:26:10.

## Workflow follow-up

- The release build's install smoke, built as a release on the accepted head, records three
  planned files in its brownfield stage and passes its MCP stage, whose list of planned files is
  exact since `release-trust-repairs`. `adopt-pin` withdrew this task to the release. The release
  run's package acceptance passes the installed command plane stage on every release leg.
- The copies run is repeated on the candidate that this lane's proof keeps. Each readable tree
  that takes the release has a passed proof on it, or is named with its reason, by the reader's
  record. No tag is created while a copy shows a new required gap or a new refusal, and the
  weekly page of the tag day states the result.
- The release head is qualified on both forges, on every platform and Python version, before the
  signed tag. The build, the publication and the journey follow by the release guide.
- The weekly page's first edition is read from `dev` by a session other than the authors'.
