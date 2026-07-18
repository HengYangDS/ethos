# repository-governance Delta

## MODIFIED Requirements

### Requirement: Advisory governance signals are visible in reader views

ETHOS SHALL expose non-blocking advisory governance signals in report and orient
reader views without treating them as transition-blocking required gaps.

#### Scenario: Report carries Work Lane coordination advisories

- **WHEN** `ethos report --json` runs and workspace status contains Work Lane coordination advisory gaps
- **THEN** the report summary includes those gaps in `advisory_gap_count`
- **AND** `gap_layers.advisory_signals.advisory_gaps` includes the Work Lane coordination advisories
- **AND** `gap_layers.advisory_signals.next_actions` routes to read-only coordination inspection commands
- **AND** the advisories do not become report `required_gaps`
