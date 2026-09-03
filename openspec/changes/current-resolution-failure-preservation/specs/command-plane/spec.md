## MODIFIED Requirements

### Requirement: Current repository decisions have one resolution owner

ETHOS SHALL resolve current role, actor, Lease, fresh Git facts, selected
official OpenSpec intent, first exact gap, and recovery action once for each
operation. Status, plan, prewrite, hook, prove, and OpenSpec archive surfaces
SHALL consume that typed resolution without reclassifying its authority, gap,
next action, or Commitment. A non-passing resolution SHALL terminate the
consumer before operation-specific planning or execution. A passing resolution
SHALL be the sole input authority for deterministic plan compilation. Effect
adapters MAY re-observe exact preconditions at CAS or Attestation issuance time
and SHALL observe the post-effect state, but they SHALL NOT reselect the
operation's intent.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, a hook, and prove evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A failed current resolution closes downstream planning

- **GIVEN** the shared current resolver returns a non-passing verdict, ordered gaps, one recovery action, and a user-decision fact
- **WHEN** a public operation consumes that resolution
- **THEN** it projects those fields unchanged and terminates before invoking its operation-specific planner, gate runner, or effect
- **AND** a command-local exception mapper cannot replace the failed resolution

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

#### Scenario: Archive planning reuses the selected intent

- **GIVEN** one archive invocation resolves a completed official Change and its Commitment
- **WHEN** archive readiness and the exact Git-effect plan are compiled
- **THEN** both consume that same current resolution
- **AND** neither rereads OpenSpec governance nor reloads Commitment

#### Scenario: Interrupted archive finalization preserves source identity

- **GIVEN** the worktree contains an exact staged official archive post-image while HEAD still contains the active Change
- **WHEN** the archive operation is resumed
- **THEN** the current resolver compiles intent once from that exact source HEAD
- **AND** the effect plan binds the same Commitment before applying exact CAS

#### Scenario: Archive post-observation does not reselect intent

- **WHEN** the admitted archive Git effect completes
- **THEN** ETHOS re-observes the resulting OpenSpec lifecycle to verify the postcondition
- **AND** that post-observation cannot replace the Commitment already bound into the plan

#### Scenario: Passing resolution freezes plan compilation

- **GIVEN** the shared current resolver returns a passing result
- **WHEN** an operation compiles its deterministic TransitionPlan
- **THEN** the planner consumes the authority, Lease generation, Commitment, scope, and Git facts from that resolution
- **AND** the planner does not reread those mutable inputs or perform a second authority decision

#### Scenario: Repository proof without active intent remains explicit

- **GIVEN** a candidate or accepted root has no active Change and no applicable archive Attestation
- **WHEN** ETHOS resolves current proof input without an explicit Change request
- **THEN** the shared resolver returns a passing repository resolution with no Commitment
- **AND** proof planning consumes that explicit result rather than ignoring an intent-resolution failure

#### Scenario: Attestation issuance rechecks mutable preconditions

- **GIVEN** a plan compiled from one passing frozen resolution
- **WHEN** ETHOS is about to issue the proof Attestation
- **THEN** the issuance owner re-observes exact HEAD, tree, repository identity, Lease generation, and invocation actor
- **AND** it rejects drift without recompiling the plan or selecting different intent
