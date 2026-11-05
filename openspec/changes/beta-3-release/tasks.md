# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.3 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports 0.2.0-beta.3
      and the release tests pass. The lane reports `ethos 0.2.0-beta.3`, and 861 release,
      architecture and CI tests pass, 1 skipped.
- [x] 1.2 Curate the `0.2.0-beta.3` entry from the Unreleased notes and the release build's audit.
      Done when the changelog validates with 0.2.0-beta.3 as its release target and the entry names
      every advisory that the audit reports. `changelog_errors` reports nothing with 0.2.0-beta.3 as
      the release target. The production-release audit at `f195a495e` reports no Python advisory and
      the two npm advisories, glob 13.0.6 and minimatch 10.2.5, that the entry names.

## Workflow follow-up

- Archive this Change after the lane's others, prove the archived head once, land, and publish
  main after hosted verification passes on every platform. Then tag, release, and dispatch the
  journey from beta.2 and alpha.29.
