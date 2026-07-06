# repository-governance Delta

## MODIFIED Requirements

### Requirement: Advisory governance signals are visible in reader views

ETHOS SHALL expose non-blocking advisory governance signals in report and orient
reader views without treating them as transition-blocking required gaps.

#### Scenario: Report exposes advisory signal count, layer, and bounded next actions

- **WHEN** `ethos report --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** `gap_layers.advisory_signals.next_actions` lists bounded inspection or explanation actions for known advisory signals
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Orient carries advisory readiness signals and actions

- **WHEN** `ethos orient --json` runs with report payload available
- **THEN** orientation readiness includes advisory signal count and items
- **AND** orientation readiness includes advisory next actions derived from report
- **AND** the human orientation output can mention advisory signals without granting mutation authority
