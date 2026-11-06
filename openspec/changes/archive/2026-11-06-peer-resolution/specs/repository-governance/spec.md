## MODIFIED Requirements

### Requirement: Publish Falls Back To Local CI When Remote Is Unavailable

ETHOS SHALL treat hosted remote publication as an adapter projection, and its local fallback
evidence SHALL be the proof admission that publication already binds, never a declared command.

#### Scenario: publish probes remote availability without blocking local readiness

- **WHEN** `ethos publish --json` runs
- **THEN** the payload includes a read-only availability observation for each declared peer under
  `remote_observations`
- **AND** remote probe failure, missing remote, or timeout remains advisory and does not create a
  required gap for local readiness
- **AND** the payload includes `local_ci_fallback` with evidence class `local_fallback`
- **AND** `local_ci_fallback.hosted_ci_status_claimed` is false

#### Scenario: local-ci fallback uses owner gates

- **WHEN** remote publication is unavailable or deferred
- **THEN** `local_ci_fallback` reports publish's admission of the proof that runs the owner's
  declared gates, in the state `admitted`, `missing`, `unavailable` or `not_required`, each with
  text
- **AND** a missing proof names `ethos prove --full --execute --expect-head <head> --json`
- **AND** local fallback evidence does not claim hosted CI pipeline success
