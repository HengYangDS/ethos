## ADDED Requirements

### Requirement: Publish Falls Back To Local CI When Remote Is Unavailable

ETHOS SHALL treat hosted remote publication as an adapter projection and provide
a local-ci fallback evidence path when the configured Git remote is unavailable.

#### Scenario: publish probes remote availability without blocking local readiness

- **WHEN** `ethos publish --json` runs
- **THEN** the payload includes a read-only `remote_availability` fact
- **AND** remote probe failure, missing remote, or timeout remains advisory and
  does not create a required gap for local readiness
- **AND** the payload includes `local_ci_fallback` with evidence class
  `local_fallback`
- **AND** `local_ci_fallback.hosted_ci_status_claimed` is false

#### Scenario: local-ci fallback uses owner gates

- **WHEN** remote publication is unavailable or deferred
- **THEN** ETHOS recommends `.config/ci/scripts/run-local-ci.sh` as local
  fallback evidence
- **AND** that script invokes reusable owner gate scripts rather than restating
  hosted CI policy inline
- **AND** local fallback evidence does not claim hosted CI pipeline success
