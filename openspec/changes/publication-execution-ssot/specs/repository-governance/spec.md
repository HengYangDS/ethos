## ADDED Requirements

### Requirement: Proposal publication is receipt-bound exact CAS

ETHOS SHALL compile every declared proposal target into one immutable
`TransitionPlan`, persist the admitted dry-run as a content-addressed request,
and apply only the exact effect recovered from that request. Apply SHALL recheck
repository identity, source HEAD, target refs, and peer-local push admission
before the first mutation.

#### Scenario: dry-run and apply share one plan

- **WHEN** proposal publication derives an admitted request and the coordinates remain unchanged
- **THEN** receipt-bound apply executes the identical plan
- **AND** every declared target advances by exact CAS

#### Scenario: a remote target drifts

- **WHEN** any target ref no longer matches its observed expected value
- **THEN** apply fails before the first push
- **AND** it reports the drifting peer and fresh observation

### Requirement: Independent peer effects remain recoverable

ETHOS SHALL treat each declared peer as an independent transaction and SHALL
NOT claim distributed atomicity. If one peer succeeds before another fails, the
terminal attestation SHALL identify applied, failed, and pending peers. Replaying
the same request SHALL preserve already-matching peers and continue safely.

#### Scenario: one peer rejects the push

- **WHEN** an earlier peer applies and a later peer rejects its exact-CAS update
- **THEN** the result is a partial effect with immutable evidence
- **AND** unchanged receipt replay converges without rewriting the applied peer

### Requirement: Publication semantics have one owner per layer

The declared peer collection SHALL be the sole topology owner. Public result
projection SHALL expose peer collections rather than single-peer aliases.
Validation, request persistence, attestation persistence, and execution SHALL
reuse their existing semantic owners instead of parallel stores or validators.

#### Scenario: several peers use one provider

- **WHEN** peer IDs and Git remotes are unique but provider labels repeat
- **THEN** topology remains valid
- **AND** each peer is independently observed and admitted

#### Scenario: no remote peer is declared

- **WHEN** local verification and installation commands are valid and peers are empty
- **THEN** local publication readiness remains valid
- **AND** no remote observation or hosted claim is manufactured
