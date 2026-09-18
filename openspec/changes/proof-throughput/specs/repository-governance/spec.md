## MODIFIED Requirements

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid Lease SHALL create and complete one selected
official Change before Commitment compilation. Selection SHALL consume exact
active identity and official artifact outputs, including when other Changes
coexist. Only those outputs are admitted; directory-wide authority is excluded.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design,
  tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier
  is admitted.

#### Scenario: Exact absent Change root resolves to metadata bootstrap

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no active official Change exists
- **WHEN** prewrite receives exactly `openspec/changes/<change>` for an absent,
  valid Change identifier
- **THEN** it returns a structured block rather than directory write authority
- **AND** its unique next action is the exact prewrite command for
  `openspec/changes/<change>/.openspec.yaml`
- **AND** it does not select archived Change authority.

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient
  Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path
  attribution
- **AND** bootstrap authority grants no additional scope or durable permission.

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** the request cannot select one active Change, an identifier is
  invalid, or a requested path is outside the selected official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does
  not authorize the write.

#### Scenario: Official creation coexists with another active Change

- **GIVEN** official new-change execution creates metadata beside another active Change
- **WHEN** every prewrite path belongs to that one existing active Change root
- **THEN** current resolution selects it and consumes its official artifact graph
- **AND** public prewrite, pre-tool and Git commit use the same admission owner
- **AND** a missing or mismatched Lease still rejects the request

#### Scenario: Ordinary work remains ambiguous

- **WHEN** product paths or several Change roots cannot identify one selected intent
- **THEN** ETHOS keeps the unresolved intent gap and marks the choice as required
- **AND** its next action inspects the official Change list rather than repeating status
- **AND** explicit plan and proof selection remain bound to the named official intent
