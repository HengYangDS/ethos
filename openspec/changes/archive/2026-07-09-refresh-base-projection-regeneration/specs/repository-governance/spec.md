## MODIFIED Requirements

### Requirement: Context-bound mutation admission

ETHOS SHALL bind tracked mutation admission and sanctioned Work Lane replay to
repository truth while preserving the boundary between semantic conflicts and
regenerable projection evidence.

#### Scenario: refresh-base resolves parity projection-only conflicts as stale projection

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts only on
  `evidence/parity/*-shadow.json`
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head> --json` runs
- **THEN** ETHOS completes the replay and returns
  `state = "base_refreshed_projection_stale"`
- **AND** the payload exposes `projection_refresh_required = true`,
  `projection_refresh_gaps`, `stale_projection_paths`, and next actions to run
  `ethos parity shadow --execute --write-evidence` before head-bound proof
- **AND** ETHOS does not report the Work Lane as ready to land until fresh proof
  admits the regenerated evidence

#### Scenario: refresh-base keeps semantic conflicts blocked

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts on any path
  outside the admitted projection set
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head> --json` runs
- **THEN** ETHOS aborts the replay and reports `refresh_base_failed`
- **AND** the Work Lane branch remains at the expected head
