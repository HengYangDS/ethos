## ADDED Requirements

### Requirement: Campaign-terminal source-budget enforcement

ETHOS SHALL permit a campaign to defer terminal source-budget settlement across
multiple locally closed Changes while retaining explicit measurement and debt
lifecycle truth.

#### Scenario: Campaign binding is exact

- **GIVEN** source-budget enforcement is `campaign_terminal`
- **WHEN** the policy is validated through the typed contract or published JSON
  Schema
- **THEN** exactly one non-empty external `campaign_id` SHALL be required
- **AND** `transition` and `terminal` policies SHALL reject `campaign_id`.

#### Scenario: Campaign-local growth remains explicit

- **GIVEN** source-budget enforcement is `campaign_terminal`
- **WHEN** the current maintained executable surface is measured
- **THEN** growth above baseline plus declared allowance SHALL appear as a
  `source_budget_campaign_growth_overage` advisory
- **AND** current-size and terminal-target non-attainment SHALL NOT by themselves
  block a Campaign-local Change
- **AND** invalid policy, aggregate declared-debt overflow, expired debt, and
  stale debt SHALL remain local blocking gaps
- **AND** terminal-target non-attainment alone SHALL be deferred to campaign
  terminal publication admission.
