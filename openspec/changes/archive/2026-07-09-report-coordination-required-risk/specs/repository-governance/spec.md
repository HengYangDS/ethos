## MODIFIED Requirements

### Requirement: Report carries Work Lane coordination blockers

ETHOS SHALL make status-required Work Lane coordination blockers visible in the
read-only report scorecard without granting cleanup authority.

#### Scenario: status-required coordination gaps exist

- **WHEN** `ethos report --json` runs for a product or adopter profile and workspace status contains required Work Lane coordination gaps
- **THEN** those required coordination gaps appear in report `required_gaps`
- **AND** `gap_layers.coordination_risk.required_gaps` carries the required coordination gaps
- **AND** product and adopter profiles both surface required coordination gaps as blockers
- **AND** advisory coordination signals remain advisory
- **AND** the report does not authorize foreign Work Lane cleanup
