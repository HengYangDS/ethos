# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.8. Done when the lane's `ethos --version` reports
      0.2.0-beta.8 and the tests that read the version or the changelog pass. The lane reports
      `ethos 0.2.0-beta.8`, and at `55bf04f9d` the test files that read `VERSION`, the CHANGELOG or
      a 0.2.0 beta version, with `tests/architecture`, ran 1,025 tests, all passing.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.8` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.8 as
      its release target and the entry names every advisory that the audit reports.
      `changelog_errors` reports nothing with 0.2.0-beta.8 as the release target. The entry names
      GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249 as a known open defect, the release audit's only
      findings at beta.7; the audit is read again before the tag.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. At `55bf04f9d` the static precheck passed and readiness passed 28 of 28 gates.
