# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.5 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports 0.2.0-beta.5
      and the tests that read the version, the npm package or the changelog pass. The lane reports
      `ethos 0.2.0-beta.5`, and at 00:07:23 the 42 test files that read the version, the npm package
      or the changelog passed with 1,023 tests.
- [x] 1.2 Curate the `0.2.0-beta.5` entry from the landed Changes and the release build's audit.
      Done when the changelog validates with 0.2.0-beta.5 as its release target and the entry names
      every advisory that the audit reports. `changelog_errors` reports nothing with 0.2.0-beta.5 as
      the release target. The audit of dev c08415158 at 23:52:55 reports GHSA-3g3m-2fjr-6pw4 and
      GHSA-g3hv-75wg-m249 and no Python advisory, and the entry names both.

## Workflow follow-up

- Refresh onto the landed `private-address-class`, prove the archived head once, land, and publish
  main after hosted verification passes on every platform. Then tag, release, and dispatch the
  journey from beta.4, beta.2 and alpha.29.
