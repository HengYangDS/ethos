# ETHOS Repository

## Purpose

ETHOS SHALL govern repository operation lifecycles: status, plan, prove, land,
publish, intake, campaign, quality, evidence, release readiness, and
self-evolution.
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

OpenSpec remains mandatory governance, not a product substrate and not a second command plane.

#### Scenario: OpenSpec validation is used
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of replacing OpenSpec with ad hoc repository parsing

### Requirement: Coupling Binding Registry
ETHOS SHALL classify product-semantic hard bindings, mandatory governance
dependencies, native protocols, self-hosting toolchains, profile or adapter
bindings, legacy evidence, and test fixtures through a machine-readable
coupling registry.

#### Scenario: Binding registry is audited
- **WHEN** `ethos quality coupling-audit --json` runs
- **THEN** the output includes `binding_registry`
- **AND** Git repository substrate and configured branch roles are classified as
  product-semantic hard bindings
- **AND** the branch role policy entry reports its configuration source,
  configuration keys, default-policy state, semantic role order, and configured
  patterns
- **AND** the standard Work Lane lifecycle command contract is classified as a
  product-semantic hard binding
- **AND** OpenSpec is classified as a mandatory governance dependency
- **AND** the official OpenSpec CLI is classified as a mandatory governance
  dependency rather than a product substrate
- **AND** command JSON, JSON Schema, claims, evidence, and ignored local state
  are classified as native protocols
- **AND** self-hosting proof tools and host projections do not own product
  semantics
- **AND** host navigation labels in product semantic docs are reported as
  required gaps

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

### Requirement: Adoption Scaffold
ETHOS SHALL generate repository governance surfaces for `.ethos`, official
OpenSpec records, repo-local skills, docs, claims, evidence placeholders, and
hosted CI projections.

#### Scenario: A repository is adopted
- **WHEN** `ethos adopt --profile gitlab --apply` runs on an empty repository
- **THEN** the planned and written files include ETHOS config, OpenSpec specs,
  `.agents/skills`, docs, claims, evidence, and GitLab CI

### Requirement: Fleet Inspection
ETHOS SHALL inspect an external repository as an adopter through repository
surfaces rather than product-core hardcoded names.

#### Scenario: An adopter is inspected
- **WHEN** `ethos fleet inspect --target <repo> --json` runs
- **THEN** ETHOS reports adopter governance surfaces and required gaps without
  embedding adopter-specific package names into the core

### Requirement: Release Policy
ETHOS SHALL expose a release policy report covering version alignment, GitLab
surfaces, protected branch/tag expectations, and attestation formats.

#### Scenario: Release policy is complete
- **WHEN** `ethos quality release-policy --json` runs in the ETHOS repository
- **THEN** the result reports no required gaps for release files, GitLab
  templates, protected refs, version alignment, and attestation formats

### Requirement: Release Attestation
ETHOS SHALL emit deterministic release attestation and SBOM projections without
publishing them as independent truth.

#### Scenario: Attestation is generated
- **WHEN** `ethos quality release-attestation --json` runs
- **THEN** the result includes an in-toto-shaped statement with SLSA-style
  builder facts and an SPDX-lite SBOM projection derived from repository
  metadata

### Requirement: Commit And Hosted Verification Policy
ETHOS SHALL distinguish current local commit/signature status from GitLab
service-side verification status without requiring tracked historical alias
metadata.

#### Scenario: Current commit policy is audited
- **WHEN** `ethos quality commits --enforce-head --json` runs
- **THEN** the result reports local identity, subject, and signature gaps
  without inferring GitLab verification from local Git output

### Requirement: Provider-neutral Self Audit
ETHOS repository lifecycle semantics SHALL accept provider reports through
explicit composition rather than importing provider execution packages.

#### Scenario: Deep self-audit is requested inside repository semantics
- **WHEN** repository self-audit runs in deep mode without an injected provider
- **THEN** it reports `openspec_reporter_not_configured`
- **AND** it does not import or execute provider-specific OpenSpec adapters

#### Scenario: Deep self-audit is composed by the command plane
- **WHEN** `ethos self audit --mode deep --json` runs in the product repository
- **THEN** the CLI composes repository self-audit with the official OpenSpec
  adapter and reports no provider-configuration gap

### Requirement: Trust-bearing Claim Admission
ETHOS SHALL review active trust-bearing claims as envelopes that bind claim,
boundary, evidence, OpenSpec carrier, fallback, kill signal, and promotion
target.

#### Scenario: Active claim is fully admitted
- **GIVEN** an active claim declares boundary owner and scope
- **AND** the claim references dated evidence with a matching SHA-256 digest
- **AND** the claim references an OpenSpec carrier when the claim is
  trust-bearing
- **AND** the claim declares fallback, kill signal, and promotion targets
- **WHEN** ETHOS checks claim governance
- **THEN** the claim report includes a trust envelope with no required gaps

#### Scenario: Active claim lacks trust carriers
- **GIVEN** an active claim lacks boundary, fallback, kill signal, OpenSpec
  carrier, or promotion target fields
- **WHEN** ETHOS checks claim governance
- **THEN** ETHOS reports required gaps naming the missing trust carrier fields

### Requirement: Proof States Distinguish Planning From Execution
ETHOS SHALL distinguish planned gate readiness from executed proof.

#### Scenario: Dry-run proof is readiness
- **WHEN** `ethos prove --json` runs without `--execute`
- **THEN** ETHOS reports `state=ready` when static checks and gate graph
  planning pass
- **AND** ETHOS does not report `state=proven`

#### Scenario: Executed proof is proven
- **WHEN** `ethos prove --execute --json` runs and all required gates pass
- **THEN** ETHOS reports `state=proven`
- **AND** every required proof run records an exit code and `state=passed`

#### Scenario: Full proof requires execution
- **WHEN** `ethos prove --full --json` runs without `--execute`
- **THEN** ETHOS reports `state=gapped`
- **AND** ETHOS reports `full_proof_requires_execute`

### Requirement: OpenSpec Lifecycle Trust Review
ETHOS SHALL review OpenSpec lifecycle readiness in addition to official
OpenSpec CLI validation.

#### Scenario: Active OpenSpec change is lifecycle complete
- **GIVEN** an active OpenSpec change has proposal, design, tasks, and delta
  specs
- **AND** a trust-bearing active claim references that change
- **WHEN** ETHOS audits OpenSpec self-governance in lifecycle mode
- **THEN** ETHOS reports the change as lifecycle-ready

#### Scenario: Active OpenSpec change lacks claim binding
- **GIVEN** an active OpenSpec change has valid official OpenSpec syntax
- **AND** no active trust-bearing claim references that change
- **WHEN** ETHOS audits OpenSpec self-governance in lifecycle mode
- **THEN** ETHOS reports `openspec_claim_binding_missing:<change>`

### Requirement: Promotion Target Readiness
ETHOS SHALL require trust-bearing claims to identify promoted repository
authority before archive or closeout can be trusted.

#### Scenario: Promotion target exists
- **GIVEN** a trust-bearing claim declares promotion targets under source,
  tests, docs, schemas, canonical OpenSpec specs, or dated evidence
- **AND** every declared promotion target exists
- **WHEN** ETHOS checks claim governance
- **THEN** the claim envelope reports promotion readiness

#### Scenario: Promotion target is missing
- **GIVEN** a trust-bearing claim declares a promotion target path that does not
  exist
- **WHEN** ETHOS checks claim governance
- **THEN** ETHOS reports `promotion_target_missing:<claim>:<path>`

### Requirement: Reference Adopter Parity Closure
ETHOS SHALL prove reference adopter parity through generic profile and shadow
evidence mechanisms rather than product-core adopter terms.

#### Scenario: Reference adopter parity is closed
- **GIVEN** tracked parity evidence for a reference adopter reports `ok=true`
- **AND** the evidence covers OpenSpec claims trust review, Work Lane
  lifecycle, proof evidence, and profile boundaries
- **WHEN** ETHOS reports parity gaps for that adopter
- **THEN** no covered capability gap is emitted for that adopter
- **AND** product-core packages remain free of adopter-private terminology
