# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.2 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-beta.2 and the release tests pass. It reports 0.2.0-beta.2, and the 139 release tests
      pass.
- [x] 1.2 Curate the `0.2.0-beta.2` entry from the four Changes and the release build's audit.
      Done when the changelog validates with 0.2.0-beta.2 as its release target and the entry
      names every advisory that the audit reports. It validates, and the audit at `58b5c6acf`
      reports no Python advisory and the eight npm advisories that the `0.2.0-alpha.22` entry
      lists.

## Workflow follow-up

- Archive this Change after the lane's other four, prove the archived head once, and land after
  hosted verification passes on every platform. Tag after beta.1's tag.
- Tell AIGW the release name, so it writes `host.toml` and starts its 7-day acceptance.
