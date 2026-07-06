# ETHOS Repository

## Purpose

ETHOS SHALL govern repository operation lifecycles: status, plan, prove, land,
publish, intake, campaign, quality, evidence, release readiness, and
evolution.
## Requirements
### Requirement: Evidence-backed Claims
ETHOS SHALL treat missing claims, missing evidence, and digest mismatches as
required gaps.

#### Scenario: Claims are audited
- **WHEN** ETHOS checks claim governance
- **THEN** every active claim is bound to dated evidence and a matching SHA-256
  digest

### Requirement: Evolution Governance
ETHOS SHALL expose hypotheses as challengeable objects and shall not mark
evolution proven from static declarations alone.

#### Scenario: Hypotheses are inspected
- **WHEN** `ethos campaign hypotheses --json` runs
- **THEN** hypotheses include campaign, state, claim, and challenge fields

### Requirement: Official OpenSpec Governance
ETHOS SHALL keep `openspec/` as an official repository governance capability for
spec-driven planning and change records while preserving `ethos ...` as the
public product command plane.

OpenSpec remains mandatory governance, not a product substrate and not a second command plane.

#### Scenario: OpenSpec validation is used
- **WHEN** ETHOS audits OpenSpec repository governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of replacing OpenSpec with ad hoc repository parsing

### Requirement: Coupling Binding Registry
ETHOS SHALL classify product-semantic hard bindings, mandatory governance
dependencies, native protocols, product toolchains, profile or adapter
bindings, historical evidence, and test fixtures through a machine-readable
coupling registry. Profile or adapter bindings SHALL carry explicit admission
metadata before they can participate in the registry.

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
- **AND** OpenSpec workspace and CLI are classified as mandatory governance
  dependencies rather than product substrate
- **AND** command JSON, JSON Schema, claims, evidence, and ignored local state
  are classified as native protocols
- **AND** product proof tools and host projections do not own product
  semantics
- **AND** profile or adapter bindings include admission authority, truth
  boundary, and decision state
- **AND** adapter or profile admission keeps `truth_boundary=profile_or_adapter`
  and `decision_state=admitted`
- **AND** host navigation labels in product semantic docs are reported as
  required gaps

#### Scenario: Adapter binding lacks admission
- **WHEN** a `profile_or_adapter_binding` lacks admission metadata
- **THEN** coupling audit reports a required gap naming the binding
- **AND** the adapter cannot silently become repository truth.

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
metadata and changed-path evidence rather than subject or identifier substring
matches.

#### Scenario: Changed scope route is explicit

- **WHEN** `ethos playbooks route --changed --mode v2-strict --json` runs
- **THEN** every selected playbook has matched changed paths, V2 routing
  evidence, operation metadata, and runnable closure obligations
- **AND** unmatched changed paths are reported as required gaps

#### Scenario: presence-only playbooks do not close report scoring

- **GIVEN** a repository only has a placeholder playbook projection
- **WHEN** `ethos report --json` runs
- **THEN** ETHOS does not give the playbook capability full score from file
  presence alone

### Requirement: Executable Capability Parity Ledger

ETHOS SHALL expose product migration parity as machine-readable command output.

#### Scenario: Shadow parity records input identity

- **WHEN** `ethos parity shadow --adopter <adopter> --target <repo> --execute --json` runs
- **THEN** the shadow parity report includes an `identity` envelope with target
  root, target HEAD, product HEAD, changed paths, compared command identities,
  and evidence input digests
- **AND** tracked parity evidence persists that identity envelope
- **AND** the shadow parity schema rejects reports that omit the identity
  envelope.

### Requirement: Fast Daily Governance Checks
ETHOS SHALL keep daily proof and report commands fast while preserving explicit
deep OpenSpec validation.

#### Scenario: Daily proof avoids deep OpenSpec
- **WHEN** `ethos prove --json` runs without `--full`
- **THEN** repository-audit uses OpenSpec shape mode
- **AND** official OpenSpec validation remains available through deep commands

### Requirement: Governed Repository Governance
ETHOS SHALL govern repositories through one governed repository semantic model.

#### Scenario: Governance context is shared
- **WHEN** ETHOS emits audit, proof, or report payloads for any governed repository
- **THEN** the payload includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** every profile classifies orient as a separate read-only reader-view
  command
- **AND** every profile classifies report as a separate read-only scorecard command
- **AND** profile or adapter differences do not create a second product command
  plane

### Requirement: Adoption Scaffold

ETHOS SHALL generate repository governance surfaces for `.ethos`, official
OpenSpec records, repo-local skills, docs, claims, evidence placeholders, and
hosted CI projections.

#### Scenario: A repository is adopted

- **WHEN** `ethos adopt --profile gitlab --apply` runs on an empty repository
- **THEN** the planned and written files include V2 skill activation metadata,
  official-quality skill package content, and package manifest records

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

### Requirement: Provider-neutral Repository Audit Composition
ETHOS repository lifecycle semantics SHALL accept provider reports through
explicit composition rather than importing provider execution packages.

#### Scenario: Deep repository-audit is requested inside repository semantics
- **WHEN** repository repository-audit runs in deep mode without an injected provider
- **THEN** it reports `openspec_reporter_not_configured`
- **AND** it does not import or execute provider-specific OpenSpec adapters

#### Scenario: Deep repository-audit is composed by the command plane
- **WHEN** `ethos audit --mode deep --json` runs in the product repository
- **THEN** the CLI composes repository repository-audit with the official OpenSpec
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
- **WHEN** ETHOS audits OpenSpec repository governance in lifecycle mode
- **THEN** ETHOS reports the change as lifecycle-ready

#### Scenario: Active OpenSpec change lacks claim binding
- **GIVEN** an active OpenSpec change has valid official OpenSpec syntax
- **AND** no active trust-bearing claim references that change
- **WHEN** ETHOS audits OpenSpec repository governance in lifecycle mode
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

### Requirement: Authority Graph Read Model
ETHOS SHALL expose a DocOS authority graph read model for current product
truth relations.

#### Scenario: Authority graph is audited
- **WHEN** `ethos audit --mode shape --json` runs
- **THEN** the result includes an authority graph report
- **AND** every graph entry has an owner, relation type, stable path, and
  typed derivation or supersession relations
- **AND** the graph reports drift gaps without becoming a lifecycle owner

### Requirement: Adopter First-Hour Contract
ETHOS SHALL provide a first-hour adopter path that starts read-only and
explains profile choice before mutation.

#### Scenario: Adoption dry-run is inspected
- **WHEN** `ethos adopt --profile python --dry-run --json` runs
- **THEN** the result reports read files, planned files, apply criteria, and
  rollback instructions
- **AND** unsupported historical profile names are rejected instead of normalized

### Requirement: OpenSpec-first governance mutation
ETHOS SHALL require a dedicated OpenSpec change, or an explicit active
non-complete OpenSpec change attachment, before non-trivial tracked mutations
to repository governance semantics.

#### Scenario: Governance design starts with OpenSpec
- **WHEN** an agent plans to change rules, skills, hook policy, product shape,
  architecture design, or governance workflow semantics
- **THEN** the agent verifies the relevant OpenSpec change with
  `openspec status --change <change> --json` before tracked mutation

#### Scenario: Complete changes are not reused silently
- **WHEN** all existing relevant OpenSpec changes are complete
- **THEN** ETHOS treats them as insufficient carriers for new semantic work
- **AND** the agent creates or selects a new non-complete change before editing

### Requirement: Context-bound mutation admission
ETHOS SHALL bind tracked mutation admission to explicit repository root,
checkout role, editor root, and target paths before a write-capable tool can
mutate tracked files.

#### Scenario: Implicit-root mutation is blocked
- **WHEN** a write-capable tool does not carry an explicit target root matching
  the current Work Lane
- **THEN** ETHOS blocks the tracked write before filesystem mutation
- **AND** reports the expected root, actual root, checkout role, and target
  paths

#### Scenario: Manual prewrite is degraded mode
- **WHEN** a host cannot install a pre-tool mutation hook
- **THEN** the agent MUST run `ethos lane prewrite <paths> --editor-root <root>
  --require-editor-root --json` before tracked writes
- **AND** the terminal design still treats manual prewrite as weaker than a
  bound mutation hook

### Requirement: Failure blocking moves upstream
ETHOS SHALL promote repeated late failures to earlier controls until the normal
workflow prevents the invalid state before mutation when practical.

#### Scenario: Late failure is promoted
- **WHEN** a repeated violation is detected after write, commit, CI, land, or
  publish
- **THEN** ETHOS records the diagnosis and promotes the control toward rule,
  hook, scaffold/template, or schema/default placement

#### Scenario: Bypassable guidance is incomplete
- **WHEN** a normal mutation path can bypass a documented guard
- **THEN** ETHOS treats the guard design as incomplete until the guard is bound
  to the mutation capability or an explicit degraded mode is declared

### Requirement: Productized OpenSpec carrier governance

ETHOS SHALL treat OpenSpec as the repository case and specification carrier,
with accepted specs, active changes, archived changes, capability profiles,
claims, and evidence refs serving distinct product duties. Archive closeout
SHALL preserve accepted scenario obligations unless an explicit removal decision
carries the deletion.

#### Scenario: Archive closeout is a product gate

- **WHEN** a Work Lane depends on a previously closed OpenSpec carrier
- **THEN** that prior carrier is archived through the official OpenSpec archive
  path before downstream campaign steps depend on it
- **AND** claims that refer to the carrier point at the dated archive path after
  archive closeout
- **AND** accepted specification obligations are fused forward rather than
  deleted by a tool-applied archive delta
- **AND** removing an accepted `WHEN`, `THEN`, or `AND` obligation requires an
  explicit removal decision instead of silent replacement.
- **AND** the campaign manifest records the lane as closed and retired before
  the next campaign step becomes active.

### Requirement: Campaign Orchestration

ETHOS SHALL model long-running productization work as campaigns that coordinate
multiple OpenSpec-backed Work Lanes and their closeout state.

#### Scenario: Campaign status reports lane steps

- **GIVEN** `evolution/campaigns/<campaign-id>/campaign.toml` exists
- **WHEN** `ethos campaign status --json` runs
- **THEN** the result includes campaign id, objective, owner, claim id, step
  summary, and ordered steps
- **AND** each step names an OpenSpec change, Work Lane branch, claim id, and
  closeout state.

#### Scenario: Campaign closeout includes campaign package

- **WHEN** `ethos campaign closeout --json` runs
- **THEN** the result includes a campaign closeout package beside local
  closeout, trust closeout, release, parity, shadow parity, and publication
  packages
- **AND** planned future steps do not block closeout before their Work Lane is
  active.

### Requirement: Productized OpenSpec Substrate

ETHOS SHALL provide an inspectable OpenSpec workspace substrate for product and
adopter repositories instead of treating an empty `openspec/` directory as
complete governance.

#### Scenario: OpenSpec substrate is inspectable

- **WHEN** ETHOS scaffolds or audits an OpenSpec workspace
- **THEN** the workspace includes guidance for the workspace, specs, and changes
- **AND** it includes family vocabulary and capability profile templates
- **AND** active changes remain case carriers rather than promoted truth.

### Requirement: Agent Invocation Admission Boundary

ETHOS SHALL describe mutation-capable agent invocation as an explicit admission
envelope over owner, target root, editor root, target paths, evidence class, and
promotion route.

#### Scenario: Invocation boundary preserves repository proof

- **WHEN** host readiness or assistant context is available
- **THEN** ETHOS may compose it as optional host evidence
- **AND** repository mutation and closeout still require Work Lane admission,
  claim binding, OpenSpec carrier readiness, and repository proof evidence.

### Requirement: Topic-scoped Evidence Closeout

ETHOS SHALL prefer topic-scoped closeout evidence bundles for long-running proof
so transcripts remain reviewable and do not become unstructured truth.

#### Scenario: Closeout evidence is reviewable

- **WHEN** a closeout proof package is summarized
- **THEN** evidence records identify topic, lane, proof class, commands, return
  codes, retained artifacts, HEAD binding, and proof boundaries.

### Requirement: Unbound Work Lane Ref Visibility

ETHOS SHALL expose configured Work Lane branch refs in workspace status even
when no linked Git worktree exists for the branch.

#### Scenario: Unbound Work Lane ref is visible but not active

- **GIVEN** a configured Work Lane branch ref exists
- **AND** no linked Git worktree exists for that branch
- **WHEN** `ethos status --json` runs
- **THEN** `branch_bindings` includes the branch with `role=work_lane` and
  `worktree_binding=unbound`
- **AND** `foreign_work_lanes` does not include that branch
- **AND** coordination reports an advisory unbound Work Lane ref signal without
  treating the ref as a blocking closeout gap.

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, and SHALL expose unbound Work
Lane refs as inspectable residue objects rather than count-only signals.

#### Scenario: Advisory unbound refs expose subjects and relation

- **GIVEN** a repository has an unbound `work/*` branch ref
- **WHEN** `ethos status --json` reports `data.coordination`
- **THEN** `unbound_work_lane_refs` includes the branch, head, claim binding,
  relation to accepted truth, and next action
- **AND** `unbound_work_lane_count` equals the number of emitted residue objects
- **AND** the signal remains advisory unless another gate reports a required gap

#### Scenario: Orientation projects unbound refs without authority

- **GIVEN** a repository has an unbound `work/*` branch ref
- **WHEN** `ethos orient --json` runs
- **THEN** `data.orientation.coordination.unbound_work_lane_refs` projects the
  branch, head, claim binding, relation to accepted truth, and next action from
  status
- **AND** the orientation view does not grant write, land, retire, or cleanup
  authority over that ref

#### Scenario: Foreign Work Lanes are observable but not owned by the current actor

- **GIVEN** a repository has a linked foreign `work/*` worktree
- **WHEN** `ethos status --json` reports that lane in `data.foreign_work_lanes`
- **THEN** the lane item exposes `current_actor_capability=observe`
- **AND** `allowed_actions` contains only `observe`
- **AND** `forbidden_actions` includes `write`, `land`, and `retire`
- **AND** write authority remains owner-only
- **AND** retirement requires the owner, accepted handoff, or maintainer
  break-glass evidence

### Requirement: Unbound Work Lane Ref Retirement

ETHOS SHALL govern local unbound Work Lane ref cleanup through explicit,
head-bound command semantics rather than raw Git branch deletion.

#### Scenario: unbound Work Lane ref retirement is head-bound

- **GIVEN** `ethos status --json` exposes an unbound Work Lane ref in
  `data.coordination.unbound_work_lane_refs`
- **WHEN** `ethos lane retire-unbound --branch <branch> --expect-head <head>
  --reason <why> --authorize --apply --json` runs
- **THEN** ETHOS deletes `refs/heads/<branch>` only if the branch is still an
  unbound configured Work Lane ref and its current head equals `<head>`
- **AND** the command emits the retired ref, reason, expected head, authorization
  state, relation to accepted truth, and required gaps

#### Scenario: unbound Work Lane ref retirement fails closed

- **WHEN** the target branch is missing, not a Work Lane, linked to a worktree,
  has a mismatched expected head, lacks a reason, or apply lacks authorization
- **THEN** ETHOS refuses deletion and reports deterministic required gaps
- **AND** the branch ref remains present
