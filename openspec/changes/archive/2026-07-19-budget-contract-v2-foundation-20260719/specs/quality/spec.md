## ADDED Requirements

### Requirement: Budget Contract v2 Migration Integrity

ETHOS SHALL preserve the versioned v1 source-budget baseline, thresholds, debt
lifecycle, inventory rules, and historical/current required or advisory
observations at their named HEADs while migrating to Budget Contract v2. The
migration SHALL introduce a typed carrier inventory and versioned,
non-compensating native metric vector before v2 can become authoritative. ELOC
SHALL remain the individual-file readability ceiling; repository-wide LOC
retirement requires a later accepted calibration and supersession decision.

#### Scenario: Foundation extraction preserves v1 behavior

- **GIVEN** the v1 source-budget command is evaluated at a stable HEAD, whether
  its policy projects blocking required gaps or campaign-terminal advisories
- **WHEN** its domain implementation moves from `ethos.domain.prove` to
  `ethos.domain.source_budget.core`
- **THEN** controlled inputs SHALL preserve taxonomy, policy facts, command
  state and exit status, baseline identity, metric classification, debt
  lifecycle, campaign binding, and required/advisory-gap semantics
- **AND** the command registry and scorecard SHALL use the new owner directly
- **AND** `ethos.domain.prove` SHALL not retain a compatibility forwarder.

#### Scenario: Migration cannot launder existing debt

- **WHEN** v2 shadow, dual control, or cutover evaluates an existing v1
  obligation
- **THEN** the v1 baseline SHALL remain
  `2dab77f169eceb2d45f917358c2a7487e7ac8db6`
- **AND** expired debt SHALL remain expired
- **AND** no average LOC-to-token conversion, allowance increase, expiry
  extension, or current-HEAD baseline reset SHALL be accepted
- **AND** a v1 required gap SHALL disappear only after settlement evidence or an
  equal-or-stronger named v2 successor obligation exists.

#### Scenario: Migration and compression completion remain distinct

- **WHEN** v2 becomes authoritative and repository-wide v1 LOC is retired
- **THEN** ETHOS MAY report Budget Contract v2 migration complete while terminal
  compression remains blocked
- **AND** compression completion SHALL additionally require every terminal
  vector to pass and active, expired, unmapped, and unclassified debt counts to
  be zero.
