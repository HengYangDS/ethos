# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.4 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports 0.2.0-beta.4
      and the release tests pass. The lane reports `ethos 0.2.0-beta.4`, and the 42 test files that
      read the version, the npm package or the changelog pass with 1,022 tests.
- [x] 1.2 Curate the `0.2.0-beta.4` entry from the landed Changes and the release build's audit.
      Done when the changelog validates with 0.2.0-beta.4 as its release target and the entry names
      every advisory that the audit reports. `changelog_errors` reports nothing with 0.2.0-beta.4 as
      the release target. The entry names the two npm advisories that the audit reports, GHSA-3g3m-2fjr-6pw4
      and GHSA-g3hv-75wg-m249, and no Python advisory.

## Workflow follow-up

- Archive this Change after the lane's others, prove the archived head once, land, and publish
  main after hosted verification passes on every platform. Run the identity-check assembler over
  beta.3's real uploads, then tag, release, and dispatch the journey from beta.3, beta.2 and
  alpha.29.
