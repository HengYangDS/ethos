## REMOVED Requirements

### Requirement: Intake Status Surface

**Reason**: A dedicated intake ledger and command are not repository authority
and duplicate provider-neutral input Attestations.

**Migration**: External intake remains adapter input; a selected Commitment
and applicable Attestations carry only the bounded facts needed by a change.

### Requirement: Executable Capability Parity Ledger

**Reason**: A parity ledger is a second currentness and evidence owner.

**Migration**: Bind independently observed provider or adopter facts to exact
Attestations selected by the applicable Commitment.

### Requirement: Fleet Inspection

**Reason**: A fleet command generalized a repository-local protocol into a
central multi-repository control plane.

**Migration**: Run the normal repository reader commands against each repository
root; each repository retains its own authority and local CAS.

### Requirement: External Retirement Readiness

**Reason**: A dedicated fleet retirement workflow duplicated repository-local
profile, proof, and lifecycle owners.

**Migration**: The target repository's status, plan, proof, and exact retirement
transition own readiness and effect.

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

**Reason**: The `unbound` command was replaced by the narrower exact
`absorbed-ref` transition and later ownerless-effect requirements.

**Migration**: Use `ethos lane retire absorbed-ref` for an exact unleased ref
already absorbed by accepted truth; other states remain blocked or use their
normal typed recovery path.

### Requirement: Ref-absent owner-unavailable partial effects are reconciled only through exact native lease CAS

**Reason**: A dedicated reconciliation command duplicated the shared exact
effect observation and recovery owner.

**Migration**: Re-enter the normal operation through fresh observation and its
operation-bound recovery receipt; do not create a second recovery command.

## MODIFIED Requirements

### Requirement: Standards Adapter Lifecycle
ETHOS SHALL adopt mature standards through adapters with explicit lifecycle,
input contract, output contract, fallback, and exit strategy.

#### Scenario: Standards are checked
- **WHEN** `ethos prove --gate repository-audit --json` runs
- **THEN** the canonical repository audit verifies each current standard adapter
  against its declared boundary, lifecycle, contracts, fallback, and retirement
  behavior

### Requirement: Changed Scope Playbook Routing

ETHOS SHALL route changed-scope skill requests through explicit activation
metadata and changed-path evidence rather than subject or identifier substring
matches.

#### Scenario: Changed scope route is explicit

- **WHEN** `ethos plan --changed --json` runs
- **THEN** every selected skill has matched changed paths, activation metadata,
  operation metadata, and runnable proof obligations
- **AND** unmatched changed paths are reported as required gaps

#### Scenario: presence-only skills do not close report scoring

- **GIVEN** a repository only has a placeholder skill projection
- **WHEN** `ethos status --json` runs
- **THEN** ETHOS does not give the skill capability full score from file
  presence alone

### Requirement: Provider-neutral Repository Audit Composition
ETHOS repository lifecycle semantics SHALL accept provider reports through
explicit proof-gate composition rather than importing provider execution
packages into the repository audit.

#### Scenario: Repository audit runs without a provider
- **WHEN** `ethos prove --gate repository-audit --json` runs
- **THEN** the repository audit evaluates repository-owned semantics without
  importing or executing provider-specific OpenSpec adapters

#### Scenario: Full proof composes official OpenSpec validation
- **WHEN** `ethos prove --full --execute --expect-head <head> --json` runs
- **THEN** the proof plan evaluates repository audit and the official OpenSpec
  gate as separate declared gates
- **AND** neither gate becomes a second lifecycle command plane
