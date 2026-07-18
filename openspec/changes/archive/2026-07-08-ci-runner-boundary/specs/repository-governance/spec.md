## MODIFIED Requirements

### Requirement: Publish Falls Back To Local CI When Remote Is Unavailable

ETHOS SHALL separate local publication readiness, remote ref publication, and
hosted CI status, and SHALL provide a local fallback evidence path when the
remote host is unavailable.

#### Scenario: local fallback separates local evidence from hosted CI success

- **WHEN** remote publication or hosted CI is unavailable
- **THEN** ETHOS recommends `tools/ci/scripts/run-local-ci.sh` as local fallback evidence
- **AND** that script invokes reusable owner gate scripts rather than restating
  hosted CI policy inline
- **AND** local fallback evidence does not claim hosted CI pipeline success

## ADDED Requirements

### Requirement: Configuration Boundary Is Script-Free

ETHOS SHALL keep executable CI and quality runners out of `.config` so
configuration, execution tools, and provider projections remain separate.

#### Scenario: reusable runners live under tools

- **WHEN** repository quality and CI runners are inspected
- **THEN** executable reusable runner scripts live under `tools/ci/scripts`
- **AND** `.config/checks/**` remains the home for tool-native quality policy
- **AND** `.config/ci/**` does not contain executable shell runners.
