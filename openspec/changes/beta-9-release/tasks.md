# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.9. Done when the lane's `ethos --version` reports
      0.2.0-beta.9 and the tests that read the version or the changelog pass. The lane reports
      `ethos 0.2.0-beta.9`, and on the tree that `b454f9db0` commits the 27 test targets that read
      `VERSION`, the CHANGELOG or a 0.2.0 beta version, with `tests/architecture`, passed 836 tests
      with 1 skipped.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.9` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.9 as
      its release target and the entry names every advisory that the audit reports.
      `changelog_errors` reports nothing with 0.2.0-beta.9 as the release target. The entry carries
      beta.8's known open defects, still open: npm 12.2.2, still the registry's latest, bundles the
      glob and minimatch that GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249 name, and CUE 0.17.1, Vale
      3.26.0 and shfmt 3.14.1 have no release built with a fixed Go; the proof's
      `dependency-vulnerabilities` gate reported nothing else, and the release audit is read again
      before the tag.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
