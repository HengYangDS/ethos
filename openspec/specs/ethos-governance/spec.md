# ETHOS Governance

## Purpose

ETHOS SHALL govern commitments, claims, evidence, schemas, standards,
OpenSpec health, release readiness, and self-evolution as one bounded
governance family.
## Requirements
### Requirement: Evidence-backed Claims
ETHOS SHALL treat missing claims, missing evidence, and digest mismatches as
required gaps.

#### Scenario: Claims are audited
- **WHEN** ETHOS checks claim governance
- **THEN** every active claim is bound to dated evidence and a matching SHA-256
  digest

### Requirement: Self Evolution
ETHOS SHALL expose hypotheses as challengeable objects and shall not mark
self-evolution proven from static declarations alone.

#### Scenario: Hypotheses are inspected
- **WHEN** `ethos campaign hypotheses --json` runs
- **THEN** hypotheses include campaign, state, claim, and challenge fields

### Requirement: Official OpenSpec Self-Governance
ETHOS SHALL keep `openspec/` as an official self-governance capability for
spec-driven planning and change records while preserving `ethos ...` as the
public product command plane.

#### Scenario: OpenSpec validation is used
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of replacing OpenSpec with ad hoc repository parsing

### Requirement: Standards Adapter Lifecycle
ETHOS SHALL adopt mature standards through adapters with explicit lifecycle,
input contract, output contract, fallback, and exit strategy.

#### Scenario: Standards are checked
- **WHEN** `ethos quality standards --json` runs
- **THEN** every standard adapter declares boundary, lifecycle, contracts,
  fallback, and retirement behavior

### Requirement: Product Design Contract
ETHOS SHALL define product truth, adopter boundaries, package ontology, and
migration safety before code migration.

#### Scenario: Design contract is audited
- **WHEN** architecture tests inspect ETHOS current governance docs
- **THEN** the product design contract, package ontology, boundary convergence
  policy, and capability parity ledger are present
- **AND** alphasim-dmgr embedded ETHOS is treated as migration oracle and
  rollback anchor rather than deleted automatically

### Requirement: Intake Status Surface
ETHOS SHALL expose intake ledger readiness through the public command plane
without treating an adopter provider as product truth.

#### Scenario: Intake status is read only
- **WHEN** `ethos intake status --json` runs without an intake provider
- **THEN** the command reports the adopter-ledger truth boundary and an
  unconfigured provider

#### Scenario: Invalid intake config is rejected
- **WHEN** `.ethos/intake.toml` exists without a provider
- **THEN** the command reports an invalid state and a required gap instead of
  claiming intake is configured

### Requirement: Changed Scope Playbook Routing
ETHOS SHALL route changed-scope playbook requests through explicit playbook
metadata rather than an implicit fallback.

#### Scenario: Changed scope route is explicit
- **WHEN** `ethos playbooks route --changed --json` runs
- **THEN** the selected playbook declares `changed-scope` in its subject
  metadata

### Requirement: Executable Capability Parity Ledger
ETHOS SHALL expose product migration parity as machine-readable command output.

#### Scenario: Parity ledger is emitted
- **WHEN** `ethos parity ledger --json` runs
- **THEN** every tracked capability has source location, target home,
  disposition, required tests, parity criterion, and rollback impact
- **AND** the unclassified capability count is zero

#### Scenario: Adopter parity gaps are reported
- **WHEN** `ethos parity gaps --adopter <name> --json` runs
- **THEN** ETHOS reports pending product migration gaps and an adopter shadow
  parity gap without mutating the adopter repository

#### Scenario: Tracked shadow evidence closes adopter parity gaps
- **GIVEN** `docs/evidence/parity/<adopter>-shadow.json` exists
- **AND** the evidence reports `shadow.ok=true` with no required gaps
- **AND** the evidence names migrated or split capabilities in
  `verified_capabilities`
- **AND** the evidence includes traceability fields for schema version,
  adopter, target, generation date, and comparison count
- **WHEN** `ethos parity gaps --adopter <adopter> --json` runs
- **THEN** ETHOS omits parity gaps for those verified capabilities
- **AND** changing a ledger disposition alone does not close the gap

#### Scenario: Incomplete shadow evidence does not close adopter parity gaps
- **GIVEN** `docs/evidence/parity/<adopter>-shadow.json` omits required
  traceability fields
- **WHEN** `ethos parity gaps --adopter <adopter> --json` runs
- **THEN** ETHOS reports a parity evidence gap
- **AND** unresolved rows remain in `data.pending_packages`

### Requirement: Fast Daily Governance Checks
ETHOS SHALL keep daily proof and report commands fast while preserving explicit
deep OpenSpec validation.

#### Scenario: Daily proof avoids deep OpenSpec
- **WHEN** `ethos prove --json` runs without `--full`
- **THEN** self-audit uses OpenSpec shape mode
- **AND** official OpenSpec validation remains available through deep commands
