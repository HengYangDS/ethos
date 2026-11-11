# Tasks

## 1. Release entry

- [x] 1.1 Move the product version to 0.2.0-beta.7. Done when the lane's `ethos --version` reports
      0.2.0-beta.7 and the tests that read the version or the changelog pass. The lane reports
      `ethos 0.2.0-beta.7` at `40e5eea26`, and at `3fc6ef9b0` the 39 test files that read `VERSION`,
      the CHANGELOG or a 0.2.0 beta version, with `tests/architecture`, ran 1,025 tests, all
      passing.
- [x] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.7` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.7 as
      its release target and the entry names every advisory that the audit reports.
      `changelog_errors` reports nothing with 0.2.0-beta.7 as the release target. The entry names
      GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249 as a known open defect: npm 12.2.2, the registry's
      latest on 2026-11-11, still requires glob ^13.0.6 and minimatch ^10.2.5. The release build's
      audit is read again before the tag.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. At `3fc6ef9b0` the static precheck passed and readiness passed 28 of 28 gates. The
      adopters' pre-check needs the landed head on the peers, so it gates the tag in the release
      procedure, not this Change.
