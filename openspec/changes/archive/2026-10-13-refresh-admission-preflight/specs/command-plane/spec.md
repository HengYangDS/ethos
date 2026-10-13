## ADDED Requirements

### Requirement: Work Lane refresh is admitted before it rewrites

`ethos lane refresh-base` SHALL check that this repository's write admission
is armed before any rebase or ref effect that would change the lane, and SHALL
report the native failure evidence of any refused refresh effect.

#### Scenario: Write admission is not armed

- **WHEN** a lane needs a refresh and the hook runtime binding reports
  required gaps
- **THEN** the refresh blocks with those gaps before rebasing or moving refs
- **AND** its continuation is the binding's own next action.

#### Scenario: A refresh effect is refused

- **WHEN** the native ref transaction or attachment of a refresh is refused
- **THEN** the result keeps its existing gaps and restoration attempt
- **AND** it carries the native process failure evidence, including the
  rejecting command's stderr and post-observation.
