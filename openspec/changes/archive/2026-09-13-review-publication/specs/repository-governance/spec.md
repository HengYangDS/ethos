## ADDED Requirements

### Requirement: Review projection is distinct from accepted publication

Review publication SHALL project an exact trusted Git object without requiring
candidate checkout identity, completed Change proof or premature archive. It
SHALL enforce the shared target-role and introduced-range obligations and exact
peer-local CAS. Accepted/release targets SHALL retain repository proof and
closeout requirements. Proposal refs SHALL not become authoring lanes.

#### Scenario: An unfinished signed snapshot enters review

- **WHEN** an admitted selected object contains an unfinished official Change and targets proposal refs
- **THEN** publication and pre-push admit review without a fabricated proof
- **AND** each selected peer receives the same object while local accepted refs remain unchanged

#### Scenario: Review and accepted targets share a request

- **WHEN** a request includes both review and accepted or release targets
- **THEN** all selected target obligations are required before the first remote effect
- **AND** the review target cannot exempt another target from proof or closeout

#### Scenario: Invalid objects or ranges are offered for review

- **WHEN** the selected signature is untrusted or introduced commits violate declared policy
- **THEN** review publication is blocked before any peer update
- **AND** the report identifies object or range admission rather than missing product proof

### Requirement: Publication replay derives proof obligations from destinations

Publication replay SHALL derive applicable proof requirements from current exact
target obligations, not from a caller-controlled proof-selection label. Review
requests SHALL not fabricate Commitment or proof records. Required proof, source
trust, target policy and observed old OIDs SHALL be checked before each effect;
unavailable outcomes SHALL remain UNKNOWN rather than permission to repeat.

#### Scenario: Review receipt replays without a proof record

- **WHEN** the exact review request remains applicable and its object and peers are unchanged
- **THEN** replay applies or recognizes the existing effect without creating a product proof
- **AND** an already matching peer is not rewritten

#### Scenario: A receipt claims review semantics for a protected target

- **WHEN** a request's carried proof selection is weakened while its target requires accepted proof
- **THEN** replay rejects the request before the first update
- **AND** self-consistent request hashes do not substitute for current target admission

#### Scenario: Required facts change after the first peer succeeds

- **WHEN** source trust, selected proof, target policy or a pending peer ref changes between effects
- **THEN** the next peer is re-observed and freshly admitted before mutation or an already-applied claim
- **AND** confirmed earlier effects are retained while a blocked peer remains untouched
- **AND** partial and unavailable outcomes remain distinct from no effect or complete publication
