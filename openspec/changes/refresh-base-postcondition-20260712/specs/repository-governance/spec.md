## ADDED Requirements

### Requirement: Work Lane refresh success is ancestry-bound

ETHOS SHALL report a successful Work Lane base refresh only when the candidate
HEAD captured before replay is an ancestor of the reported refreshed Work Lane
HEAD.

#### Scenario: zero-code replay leaves the Work Lane unrefreshed

- **GIVEN** a clean owned Work Lane is stale behind the configured candidate
  branch
- **AND** the replay subprocess returns zero without making the captured
  candidate HEAD an ancestor of the Work Lane HEAD
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
  --json` evaluates the replay result
- **THEN** ETHOS reports `state=blocked`
- **AND** it reports `refresh_base_postcondition_failed`
- **AND** it does not report `base_refreshed` or offer landing as the next
  lifecycle transition.

#### Scenario: parity-projection recovery preserves the same success condition

- **GIVEN** a stale Work Lane replays through admitted parity-projection
  recovery
- **WHEN** recovery reaches a terminal refreshed HEAD
- **THEN** ETHOS verifies the captured candidate HEAD is its ancestor before
  reporting `base_refreshed_projection_stale`
- **AND** it blocks with `refresh_base_postcondition_failed` if that fact is
  absent.
