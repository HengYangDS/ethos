## ADDED Requirements

### Requirement: Native integration distinguishes lane and incoming intent

ETHOS SHALL derive operation intent from exact native Git parent provenance,
not the count of visible Change directories. It SHALL preserve legitimate
coexisting Changes and reject ambiguous ownership without inventing completion.

#### Scenario: Independent Changes meet during merge

- **WHEN** base, lane and incoming trees identify one lane-owned Change and a
  different incoming Change
- **THEN** official lifecycle observations select the lane-owned Change
- **AND** the incoming Change remains present with its actual task state.

#### Scenario: Attribution cannot select one intent

- **WHEN** the available parent provenance identifies conflicting or multiple
  lane-owned Changes
- **THEN** the relevant operation blocks with its unresolved selection
- **AND** no unchanged status command is represented as recovery.

### Requirement: Merge continuation binds exact native state

ETHOS SHALL offer merge continuation through its existing refresh boundary.
Effects SHALL require current runtime, holder, parent and index/content
coordinates; continuing SHALL preserve both parents and declared commit policy.

#### Scenario: Pending merge is unresolved

- **WHEN** a Work Lane contains a native merge with unmerged index stages
- **THEN** status identifies that operation and its conflict paths
- **AND** it does not prescribe a new rebase or claim readiness to integrate.

#### Scenario: Resolved merge advances the lane

- **WHEN** the current owner accepts an exact resolved index and unchanged parents
- **THEN** the common commit and CAS owners create and admit the two-parent result
- **AND** proof and candidate integration remain separate subsequent obligations.

#### Scenario: Coordinates or authority change

- **WHEN** runtime, holder generation, incoming ref, index or working content no
  longer matches the preview
- **THEN** apply rejects before changing the lane ref or merge projection.

### Requirement: Native rollback preserves unique work

Before aborting a merge, ETHOS SHALL preserve its exact affected content and
native index/operation metadata. Rollback SHALL preserve unrelated and untracked
work, report uncertain effects honestly and avoid full-repository copies.

#### Scenario: Abort follows conflict resolution edits

- **WHEN** the current owner authorizes abort at exact observed merge coordinates
- **THEN** recovery material retains the conflict edits, stages and native metadata
- **AND** native rollback leaves the lane ref and unrelated content unchanged.

#### Scenario: Outcome observation or acknowledgement is lost

- **WHEN** a continuation attempt fails after a possible native effect
- **THEN** retry observes native state and exact effect evidence before acting
- **AND** it does not repeat a destructive effect solely because the prior caller
  lacked an acknowledgement.
