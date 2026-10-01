## ADDED Requirements

### Requirement: Admission output uses bounded progressive disclosure

Default JSON write-admission output SHALL use the existing result-budget owner.
Oversized detail SHALL remain in one exact-root, digest-bound artifact. Decision,
state, summary, gaps and continuation SHALL remain visible. This projection
SHALL neither change authorization nor replace fresh effect-time admission.

#### Scenario: A nested prewrite report exceeds the output ceiling

- **WHEN** `ethos lane prewrite --json` exceeds its declared budget
- **THEN** the output preserves its control fields and points to the complete original bytes
- **AND** the artifact digest and size match those bytes
- **AND** storage binds to the requested repository, not the host launch directory
- **AND** pass, block and unknown retain their existing exit and continuation semantics

#### Scenario: A small admission result needs no expansion

- **WHEN** the result fits the existing budget
- **THEN** its detail remains inline without another reader, wrapper or authority
