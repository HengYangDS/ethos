## MODIFIED Requirements

### Requirement: Control replacement preserves trusted prior verification

Control replacement SHALL read independent-verification policy from both exact
committed objects and retain the stricter mode during acceptance. Changed gate
identities SHALL remain review evidence, not implicit provider enrollment.
Applying a changed floor SHALL require explicit authorization, exact accepted
and candidate commits, current proof, fresh effect admission and CAS.

#### Scenario: Candidate cannot disable its required verifier

- **WHEN** a candidate replaces a required accepted verification policy with disabled
- **THEN** control replacement still requires evidence under the prior policy

#### Scenario: Executing authority is not an ordinary unverified change

- **WHEN** runtime selection, hook execution or Git-effect implementation changes
- **THEN** admission classifies the changed path as control and applies that policy

#### Scenario: Changed gate identities retain local-first acceptance

- **WHEN** both exact policies disable independent verification and gate execution changes
- **THEN** admission does not inspect or require host provider configuration
- **AND** the report exposes changed obligations without claiming semantic equivalence
- **AND** apply without explicit candidate selection is rejected without moving refs
- **AND** exact authorized acceptance remains reachable without an external receipt

#### Scenario: Uncommitted policy cannot change the verification requirement

- **WHEN** worktree policy differs from the selected candidate commit
- **THEN** verification selection uses the committed candidate and accepted predecessor

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

## ADDED Requirements

### Requirement: Invocation-local intent selection

ETHOS SHALL resolve an explicit command or API Change before the invocation's
`ETHOS_CHANGE`, then use applicable native inference. The selected official
intent SHALL remain an input, independent of current mutation authority.
Absent selection SHALL preserve ambiguity; invalid selection SHALL fail closed.

#### Scenario: One selected product operation spans native consumers

- **GIVEN** an owned Work Lane contains two active official Changes
- **WHEN** an invocation selects one complete Change
- **THEN** prewrite, pre-tool, native commit, plan and proof consume that intent
- **AND** explicit command selection overrides the environment input
- **AND** removing the input restores unresolved selection
- **AND** holder mismatch remains a blocking authority gap

### Requirement: Exact proof query selects intent without weakening evidence

A proof query SHALL select the requested official intent, or the intent bound
to an explicitly selected Attestation. When both are explicit, they SHALL agree. Applicable evidence SHALL retain exact
source, policy, integrity, freshness and authority checks. Distinct intents
SHALL remain distinct queries; conflicting evidence for the same query SHALL
not be resolved by choosing a convenient proof.

#### Scenario: Several intents have proofs at the same source

- **WHEN** two official Changes have current proofs for one exact commit
- **THEN** an invocation selects only its own intent's proof
- **AND** an exact Attestation selection overrides the environment choice
- **AND** an unproven selected intent cannot borrow the other proof
- **AND** malformed evidence and same-intent contradictions remain blocking

#### Scenario: Explicit archive cannot borrow another intent's proof

- **GIVEN** two official Changes share the exact source and only one has proof
- **WHEN** archive explicitly requests the unproven Change
- **THEN** admission rejects before changing refs, index or content
- **AND** an environment-selected proof for the other Change cannot satisfy it

#### Scenario: Explicit archive remains selected through post-observation

- **GIVEN** the named Change has a current exact proof
- **WHEN** archive runs with an unrelated or invalid environment selection
- **THEN** admission and post-observation consume the explicit Change
- **AND** unselected intent remains unchanged and replay observes the prior effect

#### Scenario: Explicit proof constraints must agree

- **WHEN** a query names an Attestation and a different or invalid Change
- **THEN** it rejects instead of ignoring either explicit constraint
- **AND** matching active or attested archived intent remains admissible

#### Scenario: Several completed archives retain separate proof identities

- **GIVEN** two distinct accepted intents have verified archive effects
- **WHEN** either is explicitly selected at a later shared source commit
- **THEN** its exact archived acceptance remains available for proof and planning
- **AND** both contributed requirements and product results remain intact
- **AND** absent, unreadable, invalid or unverified intent is not silently accepted

#### Scenario: Full proof shares one current intent observation with audit

- **WHEN** full proof resolves an explicit intent that differs from its ambient default
- **THEN** governance audit consumes that same resolved OpenSpec observation
- **AND** it retains independent adopter, commit and release policy checks
- **AND** a new invocation observes current inputs rather than cached permission

### Requirement: External verification recovery follows its owning prerequisite

Required independent verification SHALL validate the configured provider before
requesting its receipt. Control replacement and publication SHALL share that
owner and report an actionable prerequisite without inventing evidence paths.
Optional unselected verification SHALL preserve local-first behavior.

#### Scenario: The required provider is unavailable

- **WHEN** its protected configuration is missing, unreadable or invalid
- **THEN** admission identifies that provider prerequisite and requests operator repair
- **AND** no repository effect or executable retry is presented as the repair

#### Scenario: A configured provider has no valid receipt

- **WHEN** evidence is absent, outside the protected store, stale or incorrectly bound
- **THEN** admission requests valid evidence from the configured provider
- **AND** its configured store and issuer remain distinct from repository private state
- **AND** valid signatures, freshness and exact bindings are all required for success
