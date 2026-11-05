# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-beta.1 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-beta.1 and the release tests pass. It reports 0.2.0-beta.1, and the 139 release tests
      pass.
- [x] 1.2 Curate the `0.2.0-beta.1` entry. Done when the changelog validates with 0.2.0-beta.1 as
      its release target and names the criteria, the journeys not qualified and the known open
      defects. It validates with no error.

## Workflow follow-up

- Tag only after alpha.30's release run passed both journey legs and this head's hosted runs
  passed on every supported platform.
