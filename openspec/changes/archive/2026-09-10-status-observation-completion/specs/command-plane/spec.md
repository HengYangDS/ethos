## ADDED Requirements

### Requirement: Reader Observation Completion

ETHOS readers SHALL select continuation from actual pending operations and
unobserved facts. A complete passing observation with neither SHALL have an
empty next action and continuation done. Reader completion SHALL NOT assert
completion of the repository, external delivery or unrelated work.

#### Scenario: Passive accepted checkout has no pending operation

- **WHEN** accepted and candidate coordinates agree and no blocking gap or
  unobserved coordination detail remains
- **THEN** status and lane status return an empty next action and continuation done
- **AND** they do not require a new Change or store observation progress

#### Scenario: Coordination detail is expanded once

- **WHEN** compact status has foreign or unbound lanes requiring detail
- **THEN** it may select the existing lane-status reader
- **AND** complete lane status preserves the coordination facts without selecting itself
- **AND** observation does not authorize writing or retiring foreign content

#### Scenario: Accepted candidate still needs closeout

- **WHEN** a candidate is a distinct admissible successor of accepted HEAD
- **THEN** both readers reuse the same exact closeout derivation
- **AND** they do not replace that operation with done or a re-observation loop

#### Scenario: A necessary input is blocked or unavailable

- **WHEN** current authority, topology or scope cannot admit progress
- **THEN** the existing blocking or unknown verdict and its cause are preserved
- **AND** the absence of a next action does not turn that result into done
