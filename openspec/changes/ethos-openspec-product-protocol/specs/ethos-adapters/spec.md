## MODIFIED Requirements

### Requirement: Native OpenSpec Adapter

ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
review.

#### Scenario: OpenSpec adapter reports lifecycle carriers

- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the report includes official OpenSpec doctor, list, status, and
  strict validation command results
- **AND** each active change reports proposal, design, tasks, delta spec, claim
  binding, and proposal protocol state.

#### Scenario: Proposal protocol gaps are product gaps

- **GIVEN** an active OpenSpec change has a proposal capability entry
- **WHEN** lifecycle review runs
- **THEN** ETHOS reports gaps for unknown live capabilities, missing capability
  profiles, missing subject/reuse/change/facet metadata, invalid reuse or
  change values, and missing out-of-scope boundaries.

