# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.6 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports 0.2.0-beta.6
      and the tests that read the version, the npm package or the changelog pass. The lane reports
      `ethos 0.2.0-beta.6`, and at 08:37:01 the 53 test files that read the version, the npm package
      or the changelog passed with 1,341 tests.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.6` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.6 as
      its release target and the entry names every advisory that the audit reports.
      `changelog_errors` reports nothing with 0.2.0-beta.6 as the release target. The audit of the
      peer-resolution proof at 08:14 reports GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249 and no
      Python advisory, and the entry names both.
