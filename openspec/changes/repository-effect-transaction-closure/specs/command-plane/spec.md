## REMOVED Requirements

### Requirement: Commitment rebind coordinates are publicly derived

**Reason**: Rebind existed only because Lease and tracked Commitment carriers
mirrored moving repository facts.

**Migration**: Re-observe Git and official OpenSpec facts for each plan; use the
common repository-effect executor for exact CAS and recovery.

### Requirement: Commitment rebind apply consumes an exact receipt

**Reason**: A separate rebind transaction is not part of the terminal model.

**Migration**: Existing repository effects consume their own exact plan and
effect Attestation; no compatibility command remains.

### Requirement: Commitment rebind failures are directly actionable

**Reason**: Rebind-specific remediation preserves a retired state machine.

**Migration**: Report the actual Lease, Git, OpenSpec, or effect boundary and the
single public command owned by that boundary.

### Requirement: Start Change accepts explicit predecessor identities

**Reason**: Persisted predecessor sets duplicate Git history and turn archived
OpenSpec into an active database.

**Migration**: Bind a prior Attestation only when it changes current admission;
derive ordinary lineage from Git and archived OpenSpec.

## MODIFIED Requirements

### Requirement: Current Work Lane authority has one fresh resolver

ETHOS SHALL resolve tracked-write authority from the current worktree, branch
role, invocation actor, and exact four-field Lease. It SHALL read HEAD, tree,
index, changed paths, and official OpenSpec intent as fresh facts. Historical
transition Attestations SHALL provide provenance only and SHALL NOT mint,
revoke, or replace current authority.

#### Scenario: Current binding is exact without historical transition evidence

- **GIVEN** the invocation actor owns a valid Lease for the current Work Lane
- **AND** the current checkout has one valid active official OpenSpec Change
- **WHEN** status, plan, prewrite, or pre-commit resolves authority
- **THEN** every surface projects the same passing Lease and fresh repository facts
- **AND** no carrier, rebind, or historical effect record is required

#### Scenario: Current binding is stale or ambiguous

- **WHEN** the actor, Lease generation, branch role, Git facts, or selected official Change is missing or ambiguous
- **THEN** every consuming surface fails closed with the same first exact reason
- **AND** historical transition evidence cannot override the mismatch

#### Scenario: Historical transition evidence remains provenance

- **WHEN** valid transition Attestations are available
- **THEN** path attribution and effect verification may cite them
- **AND** removing them changes provenance detail only, not a valid current authoring verdict
