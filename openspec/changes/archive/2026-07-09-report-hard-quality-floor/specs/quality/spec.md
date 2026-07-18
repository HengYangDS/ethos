## MODIFIED Requirements

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: Report exposes hard quality-floor gaps

- **WHEN** a product hard quality gate such as Python size, module layout,
  coverage, type policy, or public-surface docstrings reports required gaps
- **THEN** `ethos report --json` includes those gaps in its blocking
  `required_gaps`
- **AND** the report state is not ready
- **AND** the report payload includes a `hard_quality_floor` read model with the
  contributing gate verdicts
- **AND** next actions point to the concrete standalone quality command instead
  of implying full proof can close the gap

#### Scenario: Coverage writer lock is visible during owner-gate execution

- **WHEN** `ethos quality coverage --json` runs while the Python test owner
  script holds `build/evidence/quality/tests/coverage/.write.lock` and the latest
  coverage XML is temporarily absent
- **THEN** ETHOS reports the coverage artifact writer as in-progress advisory
  state
- **AND** the missing artifact is not promoted into a stale hard quality gap until
  the owner writer lock is released
- **AND** `ethos report --json` can run during the test gate without converting
  in-flight evidence generation into a false required gap.
