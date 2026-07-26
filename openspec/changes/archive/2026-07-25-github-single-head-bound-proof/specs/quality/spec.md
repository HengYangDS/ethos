## ADDED Requirements

### Requirement: Hosted Repository Proof Executes One Full Test Graph

ETHOS SHALL project each hosted repository-proof job through one authoritative
HEAD-bound proof entrypoint and SHALL NOT execute the same complete unit and
architecture test gate separately before that proof.

#### Scenario: GitHub repository proof executes the default test gate once

- **GIVEN** the default `ethos prove --execute` graph includes the
  `unit-architecture` gate owned by `tools/ci/scripts/run-python-tests.sh`
- **WHEN** the GitHub self-hosted macOS repository-proof job evaluates a commit
- **THEN** the provider projection invokes
  `tools/ci/scripts/run-head-bound-proof.sh` exactly once
- **AND** the provider projection does not invoke
  `tools/ci/scripts/run-python-tests.sh` as a separate job step
- **AND** the nested test gate receives the declared two-worker, 300-second,
  signal-timeout environment
- **AND** proof and readiness artifacts are uploaded even when the proof fails
- **AND** GitLab and the canonical proof gate registry remain unchanged.
