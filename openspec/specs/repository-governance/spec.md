# ETHOS Repository Governance

## Purpose

ETHOS SHALL govern repository operation lifecycles: status, plan, prove, land,
publish, intake, campaign, quality, evidence, release readiness, and
evolution.
## Requirements
### Requirement: Semantic OpenSpec Capability Layout

ETHOS SHALL identify accepted OpenSpec capabilities by stable product semantics
rather than implementation package names.

#### Scenario: accepted specs use semantic capability IDs
- **WHEN** repository audit inspects `openspec/specs`
- **THEN** the required capability directories are `kernel`, `contracts`,
  `repository-governance`, `adapters`, `command-plane`,
  `assistant-projections`, `distribution`, `quality`, and `proof-hosts`
- **AND** no accepted capability directory is required merely because it mirrors
  a retired package or host surface name
- **AND** `capability.toml` records implementation ownership as metadata rather
  than capability identity

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

### Requirement: Evolution Ledger Protocol
ETHOS SHALL keep reviewed evolution records and active hypotheses in one
repository-truth ledger at `evolution/ledger.toml`.

#### Scenario: workflow runtime bridges to evolution without owning it
- **WHEN** ETHOS projects workflow runtime readiness for a research, hypothesis, experiment, or campaign-driven change
- **THEN** the runtime projection references the evolution ledger or campaign manifest when present
- **AND** hypotheses, experiments, evaluations, canonization, and retirement remain governed by evolution records, OpenSpec carriers, claims, evidence, and Chronicle
- **AND** runtime state does not replace `ethos campaign hypotheses`, `ethos campaign status`, or `ethos quality evidence-freshness` as evolution governance surfaces

### Requirement: Practice Selection And Fate
ETHOS SHALL support governed practice claims, evidence-weighted selection among
competing hypotheses, designs, adapters, method packs, or implementation
strategies, and explicit practice fate decisions: introduce, compose, refine,
supersede, retire, or reject.

#### Scenario: practice claim carries commitment effect
- **WHEN** ETHOS evaluates a reusable practice or framework-family proposal
- **THEN** the ledger records a practice claim with subject, question, claim, boundary, falsifiers, incumbent relation, candidate set, experiment protocol, evaluation record, commitment effect, practice-change refs, commitment targets, evidence refs, and decision refs
- **AND** the practice claim remains an evolution carrier for effects on governed commitments rather than the root authority
- **AND** candidate sets, experiments, evaluations, practice-change records, runtime nodes, task graphs, and method packs remain subordinate projections of that claim

#### Scenario: candidate set is evaluated
- **WHEN** ETHOS compares multiple candidate practices for the same governance question
- **THEN** the candidates are represented as research, hypotheses, experiments, eval metadata, reviews, claims, evidence, or OpenSpec carriers
- **AND** the selected practice records why it wins over alternatives
- **AND** rejected candidates are archived, retired, or retained as bounded learning

#### Scenario: practice fate is classified
- **WHEN** ETHOS classifies a practice change
- **THEN** the practice-change record states whether it introduces, composes, refines, supersedes, retires, or rejects a practice, and records boundary, commitment effect, evidence, decision refs, and incumbent-specific migration or retirement fields when applicable
- **AND** the practice fate is recorded through evolution records, claim/evidence/chronicle rather than hidden runtime state

#### Scenario: ledger records candidate selection objects
- **WHEN** `evolution/ledger.toml` records a candidate selection decision
- **THEN** it includes a practice claim with commitment effect, a candidate set with at least two candidates, a bounded experiment protocol, an evaluation record with selected and rejected candidates, and a practice-change record that distinguishes introduction from real supersession and retirement
- **AND** every object binds evidence and decision refs instead of relying on assistant memory

### Requirement: Practice Evolution Kernel
ETHOS SHALL govern tools, frameworks, workflows, skills, task graphs, scenario
systems, and specs as practice carriers rather than as authorities.

#### Scenario: practice is judged before carrier adoption
- **WHEN** ETHOS evaluates an external framework or internal workflow proposal
- **THEN** the evaluation identifies the practice being tested, the evidence that would confirm or falsify it, the repository commitment effect it would create, compose, refine, replace, remove, or reject, and the correct fate after judgment
- **AND** the fate is one of introduce, compose, refine, supersede, retire, or reject according to its relation to incumbent boundaries
- **AND** no carrier becomes lifecycle truth without source, schema, OpenSpec, claim, evidence, and Chronicle promotion

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
- **AND** a reference-adopter embedded governance implementation is treated as a
  migration oracle and rollback anchor rather than deleted automatically

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

#### Scenario: Shadow parity rejects external false negatives

- **GIVEN** an embedded fallback command reports a blocking required gap
- **WHEN** the external ETHOS product omits that required gap or only reports it
  as advisory
- **THEN** shadow parity reports a blocking `shadow_false_negative:<command>` gap
- **AND** tracked parity evidence cannot close adopter retirement parity unless
  it records zero false negatives

### Requirement: Fast Daily Governance Checks
ETHOS SHALL keep daily proof and report commands fast while preserving explicit
deep OpenSpec validation.

#### Scenario: Daily proof avoids deep OpenSpec
- **WHEN** `ethos prove --json` runs without `--full`
- **THEN** repository-audit uses OpenSpec shape mode
- **AND** official OpenSpec validation remains available through deep commands

### Requirement: Governed Repository Governance

ETHOS SHALL govern repositories through one governed repository semantic model.

#### Scenario: Governance context is shared in audit, proof, and report payloads

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
- **AND** first-glance product docs name this as Isomorphic Governance without
  turning governed repositories into product clones.

#### Scenario: Primary command results expose the shared governance context

- **WHEN** ETHOS emits `status`, `plan`, `prove`, `land`, `publish`, `orient`, or
  `report` JSON for any governed repository
- **THEN** the top-level result includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** every profile classifies orient as a separate read-only reader-view
  command
- **AND** every profile classifies report as a separate read-only scorecard
  command
- **AND** profile or adapter differences do not create a second product command
  plane
- **AND** command-specific `data` payloads remain governed by their own native
  schema or domain contract rather than becoming a second truth store.

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names.

#### Scenario: Common docs kernel is audited

- **WHEN** `ethos quality docs-topology --json` runs
- **THEN** ETHOS requires the common docs kernel: `docs/README.md`,
  `docs/decisions/`, `docs/evidence/`, `docs/history/`, and `docs/reference/`
- **AND** the required kernel is invariant across single-repository, monorepo,
  and multi-repository governed subjects
- **AND** product or adopter extension roots remain optional and domain-bounded
- **AND** required kernel docs expose supported state metadata instead of using
  `current` or `future` as state values

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and
  does not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order, contracts,
  evidence, claims, and proof rather than by directory name
- **AND** unlanded intent belongs in OpenSpec changes, plans, research, or
  decision revisit triggers rather than in a generic intent directory

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, start, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

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

### Requirement: External Retirement Readiness
ETHOS SHALL determine whether an adopted repository can retire its embedded
ETHOS backend through generic repository profile, product-boundary, parity,
shadow, and lifecycle checks rather than product-core adopter directories.

#### Scenario: Retirement readiness is inspected
- **WHEN** `ethos fleet retirement-readiness --target <repo> --json` runs
- **THEN** ETHOS reads the target repository's `.ethos/profile.toml`
- **AND** validates declared binding roots such as `.config/`
- **AND** rejects profile-declared forbidden product-core adopter roots in the
  ETHOS product repository
- **AND** includes parity and shadow false-negative evidence in the verdict
- **AND** reports external-default, embedded-freeze, rollback-window evidence,
  and final retirement lifecycle gaps separately from parity and product-boundary gaps
- **AND** requires a tracked rollback-window evidence manifest with completed
  `proof_report`, `work_lane_closeout`, `domain_gate`, and `assistant_playbook`
  scenarios before accepting a terminal retirement-ready backend state
- **AND** requires the rollback-window manifest to be repository-local,
  Git-tracked, parseable, bound to reachable adopter and external-product
  heads, and backed by per-scenario evidence path, command, digest, target-head,
  and product-head fields
- **AND** does not require `adopters/<name>`, `profiles/<name>`, or
  `tests/fixtures/adopters/<name>` inside the ETHOS product repository.

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

### Requirement: Land readiness is proof-grounded

ETHOS SHALL NOT report a Work Lane as ready to land unless the current HEAD has
valid executed proof evidence.

#### Scenario: Work Lane land dry-run without executed proof is blocked

- **GIVEN** a clean Work Lane with no structural landing gaps
- **AND** no valid executed proof record exists for the Work Lane HEAD
- **WHEN** `ethos land --json` evaluates the Work Lane
- **THEN** ETHOS reports `proof_not_proven`
- **AND** ETHOS does not report `ready_to_land`
- **AND** the payload exposes `proof_readiness.head` bound to the current HEAD
- **AND** the next action is `ethos prove --execute --expect-head <HEAD> --json`

#### Scenario: Work Lane land dry-run with executed proof is ready

- **GIVEN** a clean Work Lane with no structural landing gaps
- **AND** a valid executed proof record exists for the Work Lane HEAD
- **WHEN** `ethos land --json` evaluates the Work Lane
- **THEN** ETHOS reports `ready_to_land`
- **AND** `proof_readiness.state` is `proven`

### Requirement: Accepted-root closeout distinguishes current from promotable

ETHOS SHALL NOT describe an already-synchronized accepted root and candidate
branch as ready for another closeout mutation.

#### Scenario: Accepted-root closeout is already current

- **GIVEN** the accepted root and configured candidate branch resolve to the same
  HEAD
- **WHEN** `ethos land --closeout --json` evaluates accepted-root closeout
- **THEN** ETHOS reports `state=accepted_current`
- **AND** `closeout_bootstrap.state` is `current`
- **AND** the next action is `ethos publish`
- **AND** ETHOS does not report `ready_to_closeout`

#### Scenario: Accepted-root closeout apply is a no-op when already current

- **GIVEN** the accepted root and configured candidate branch resolve to the same
  HEAD
- **WHEN** `ethos land --closeout --apply --authorize --expect-head <HEAD>
  --json` runs
- **THEN** ETHOS reports `state=accepted_current`
- **AND** no new proof is required for a candidate head that is already accepted
- **AND** the accepted root remains at the same HEAD

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
mutate tracked files. ETHOS SHALL also reject hidden change carriers that bypass
repository truth surfaces.

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

#### Scenario: Worktree root binding fails closed

- **WHEN** ETHOS resolves mutation admission from inside a linked Work Lane
  subdirectory
- **THEN** the default target root is the current Git worktree root rather than
  an accepted root or process launch directory
- **AND** product-repository prewrite blocks when the command runner, schema
  source, and audited root do not bind to the same product checkout

#### Scenario: Sanctioned Work Lane replay keeps admission context

- **GIVEN** `ethos lane refresh-base --apply --authorize --expect-head <head>`
  is replaying a clean owned Work Lane onto the configured candidate branch
- **WHEN** Git temporarily detaches HEAD during rebase and the commit-time
  fallback hook evaluates staged tracked paths
- **THEN** mutation admission derives the effective branch role from Git rebase
  `head-name` only when it names a configured `work/*` branch
- **AND** the hook still checks the same repository root, editor root, runtime
  binding, and target paths
- **AND** detached replay for accepted, candidate, submit, other, or unknown
  branches remains protected and fails closed

#### Scenario: refresh-base resolves parity projection-only conflicts as stale projection

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts only on
  `evidence/parity/*-shadow.json`
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
  --json` runs
- **THEN** ETHOS completes the replay and returns
  `state = "base_refreshed_projection_stale"`
- **AND** the payload exposes `projection_refresh_required = true`,
  `projection_refresh_gaps`, `stale_projection_paths`, and next actions to
  regenerate parity evidence before head-bound proof
- **AND** ETHOS does not report the Work Lane as ready to land until fresh proof
  admits the regenerated evidence

#### Scenario: refresh-base keeps semantic conflicts blocked

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts on any path
  outside the admitted projection set
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
  --json` runs
- **THEN** ETHOS aborts the replay and reports `refresh_base_failed`
- **AND** the Work Lane branch remains at the expected head

#### Scenario: Stash mutation is rejected before shell execution

- **WHEN** hook admission evaluates a pre-run shell command that would create,
  apply, pop, drop, clear, store, or implicitly create a Git stash
- **THEN** ETHOS blocks the command with `git_stash_forbidden`
- **AND** the command is not admitted as a backup, handoff, residue, or closeout
  carrier

#### Scenario: Protected-root pollution is classified before recovery

- **GIVEN** tracked dirty work is discovered in an accepted, candidate, or
  release-root checkout outside audited closeout semantics
- **WHEN** the work is evaluated for recovery
- **THEN** useful work is moved into an owned Work Lane with visible evidence
- **AND** useless or unsafe pollution is reverted from the protected root
- **AND** hidden carriers such as Git stash are forbidden as backup, handoff,
  residue, or closeout state

#### Scenario: Stash observation remains available for forensics

- **WHEN** hook admission evaluates `git stash list` or `git stash show`
- **THEN** ETHOS treats the command as observation-only
- **AND** the observation does not authorize using stash as repository truth

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
- **AND** it includes capability vocabulary and capability profile templates
- **AND** active changes remain case carriers rather than promoted truth.

#### Scenario: OpenSpec metadata compatibility is checked upstream

- **WHEN** ETHOS performs the always-run OpenSpec shape audit
- **THEN** it checks active and archived `.openspec.yaml` metadata for keys
  accepted by the official OpenSpec editor model
- **AND** unsupported metadata keys are reported as repository governance gaps
  before an IDE or host projection attempts to parse the workspace.

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
  treating the ref as a blocking closeout gap
- **AND** the advisory signal classifies into the invalid-state taxonomy instead
  of `unclassified_invalid_state`.

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

#### Scenario: Status summary exposes coordination small signals

- **WHEN** `ethos status --json` reports `data.coordination`
- **THEN** `summary.foreign_work_lane_count` equals
  `data.coordination.foreign_work_lane_count`
- **AND** `summary.unbound_work_lane_count` equals
  `data.coordination.unbound_work_lane_count`
- **AND** `summary.coordination_blocking` equals `data.coordination.blocking`
- **AND** those summary fields remain derived visibility signals and do not grant
  write, land, retire, or cleanup authority over another Work Lane or ref

#### Scenario: Lane status summary exposes coordination small signals

- **WHEN** `ethos lane status --json` reports `data.coordination`
- **THEN** `summary.foreign_work_lane_count` equals
  `data.coordination.foreign_work_lane_count`
- **AND** `summary.unbound_work_lane_count` equals
  `data.coordination.unbound_work_lane_count`
- **AND** `summary.missing_lease_count` equals
  `data.coordination.missing_lease_count`
- **AND** `summary.coordination_advisory_count` equals the number of
  `data.coordination.advisory_gaps`
- **AND** `summary.coordination_blocking` equals `data.coordination.blocking`
- **AND** `summary.coordination_next_action` equals
  `data.coordination.next_action`
- **AND** those summary fields remain derived visibility signals and do not grant
  write, land, retire, or cleanup authority over another Work Lane or ref

#### Scenario: Orientation projects unbound refs without authority

- **GIVEN** a repository has an unbound `work/*` branch ref
- **WHEN** `ethos orient --json` runs
- **THEN** `data.orientation.coordination.unbound_work_lane_refs` projects the
  branch, head, claim binding, relation to accepted truth, and next action from
  status
- **AND** `data.orientation.coordination.next_action` projects
  `status.data.coordination.next_action` as coordination guidance
- **AND** `summary.unbound_work_lane_count` equals
  `data.orientation.coordination.unbound_work_lane_count`
- **AND** human `ethos orient` output renders coordination guidance as at most
  one concise coordination line
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

#### Scenario: Foreign Work Lanes expose closeout disposition without authority

- **GIVEN** a repository has a linked foreign `work/*` worktree
- **WHEN** `ethos status --json` reports that lane in `data.foreign_work_lanes`
- **THEN** the lane item exposes `relation_to_accepted` and
  `closeout_disposition` derived from Git relation, dirty state, lease, and
  claim binding
- **AND** closeout residue appears as a coarse advisory coordination signal
  rather than one branch-level gap per disposition
- **AND** missing leases remain distinct from retire-ready closeout disposition
- **AND** a clean claim-bound lane absorbed by accepted truth reports a
  head-bound `next_action` for `ethos lane retire-landed --branch <branch>
  --expect-head <head> --apply --json`
- **AND** `ethos report --json` routes that advisory signal to read-only
  inspection commands
- **AND** the disposition does not grant write, land, retire, or cleanup
  authority over that Work Lane

#### Scenario: Foreign Work Lane missing physical path is fail-soft and observe-only

- **GIVEN** Git worktree metadata advertises a foreign `work/*` Work Lane path
- **AND** that physical path no longer exists
- **WHEN** `ethos status --json` or accepted-root closeout readiness reads Work
  Lane coordination state
- **THEN** ETHOS reports the foreign lane with `worktree_binding=missing`
- **AND** the reader does not crash while inspecting dirty paths
- **AND** `dirty=false` and `dirty_paths=[]` because no dirty filesystem state is
  observable at that path
- **AND** coordination remains advisory for accepted-root readers
- **AND** the payload grants no write, land, retire, or cleanup authority over
  the foreign lane

#### Scenario: Candidate Worktree missing physical path is fail-soft

- **GIVEN** Git worktree metadata advertises the configured candidate worktree path
- **AND** that physical path no longer exists
- **WHEN** `ethos status --json` reads workspace status
- **THEN** ETHOS reports the candidate with `worktree_binding=missing`
- **AND** `worktree_exists=false`
- **AND** readiness reports `candidate_worktree_missing` instead of crashing while
  checking candidate dirty state
- **AND** if the candidate path disappears during dirty inspection, ETHOS treats
  the candidate state as unsafe to close out rather than crashing

#### Scenario: Candidate absent or unbound binding remains schema-valid

- **GIVEN** an adopted repository has not yet created the configured candidate
  branch
- **WHEN** `ethos status --json` reads workspace status
- **THEN** ETHOS reports the candidate with `worktree_binding=absent`
- **AND** the workspace-status schema accepts that candidate read-model state
- **AND** actual worktree list entries remain limited to physical bindings
  `current`, `linked`, or `missing`
- **AND** if the candidate branch exists without a candidate worktree, ETHOS
  reports the candidate with `worktree_binding=unbound` without using `unbound`
  for actual worktree entries

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

### Requirement: Landed Work Lane Retirement

ETHOS SHALL govern local landed Work Lane cleanup through explicit,
head-bound command semantics rather than raw Git worktree or branch deletion.

#### Scenario: landed Work Lane retirement is head-bound

- **GIVEN** `ethos status --json` exposes a linked Work Lane whose branch is
  already merged into the accepted root
- **WHEN** `ethos lane retire-landed --branch <branch> --expect-head <head>
  --apply --json` runs
- **THEN** ETHOS removes the linked worktree and deletes `refs/heads/<branch>`
  only if the Work Lane is clean, merged, explicitly selected, and its current
  head equals `<head>`
- **AND** the command emits the selected branch, expected head, ref, retired
  lane, and required gaps

#### Scenario: landed Work Lane retirement fails closed

- **WHEN** the selected Work Lane is missing, dirty, unmerged, lacks an
  expected head, or has a mismatched expected head
- **THEN** ETHOS refuses cleanup and reports deterministic required gaps
- **AND** the Work Lane branch ref remains present

#### Scenario: landed Work Lane retirement actor authority is visible

- **GIVEN** a linked Work Lane has an active lease owner
- **WHEN** `ethos lane retire-landed --branch <branch> --expect-head <head>
  --apply --json` runs without an actor binding matching the lease owner
- **THEN** ETHOS refuses cleanup with `foreign_work_lane_retire_authority_required`
- **AND** the command payload exposes the actor source, current actor binding
  state, required lease owner, selected ref, and expected head
- **AND** the command emits a bounded next action to bind the actor or obtain
  owner handoff
- **AND** the Work Lane worktree and branch ref remain present

### Requirement: Superseded Linked Work Lane Retirement

ETHOS SHALL govern cleanup of clean linked Work Lanes whose semantic truth has
already been absorbed into accepted root without requiring their stale branch
content to be landed.

#### Scenario: superseded linked Work Lane retirement is head, actor, reason, and absorption bound

- **GIVEN** a linked clean `work/*` Work Lane is not merged into accepted root
- **WHEN** `ethos lane retire-superseded --branch <branch> --expect-head <head>
  --absorbed-by <accepted-head> --reason <why> --authorize --apply --json` runs
- **THEN** ETHOS removes the linked worktree and deletes `refs/heads/<branch>`
  only if `<head>` still matches the branch, `<accepted-head>` equals the current
  accepted root, accepted-root tree content matches the lane's changed paths,
  the lane lease owner matches `ETHOS_ACTOR`, and a reason is supplied
- **AND** the command emits the retired lane, reason, absorption head, mutation
  binding, and required gaps

#### Scenario: superseded linked Work Lane retirement fails closed

- **WHEN** the lane is missing, unlinked, dirty, already merged, actor mismatched,
  head mismatched, absorption head stale or missing, reason missing, or apply
  lacks authorization
- **THEN** ETHOS refuses cleanup and reports deterministic required gaps
- **AND** the Work Lane worktree and branch ref remain present

### Requirement: Evolution Ledger Single Source Of Truth

ETHOS SHALL keep reviewed evolution records and active hypotheses in one
repository-truth ledger at `evolution/ledger.toml`.

#### Scenario: evolution commands and gates use one ledger

- **WHEN** ETHOS reports campaign hypotheses, validates schemas, audits release
  files, or projects assistant governance resources
- **THEN** those surfaces use `evolution/ledger.toml`
- **AND** documentation may explain evolution governance without storing a
  parallel ledger
- **AND** the ledger schema accepts typed evolution entries and hypothesis
  records in the same document
- **AND** non-campaign evolution entries bind at least one evidence ref and one
  decision ref
- **AND** active hypothesis proof, review, and decision refs resolve to known
  ETHOS command references or repository paths

### Requirement: Publish Falls Back To Local CI When Remote Is Unavailable

ETHOS SHALL treat hosted remote publication as an adapter projection and provide
a local-ci fallback evidence path when the configured Git remote is unavailable.

#### Scenario: publish probes remote availability without blocking local readiness

- **WHEN** `ethos publish --json` runs
- **THEN** the payload includes a read-only `remote_availability` fact
- **AND** remote probe failure, missing remote, or timeout remains advisory and
  does not create a required gap for local readiness
- **AND** the payload includes `local_ci_fallback` with evidence class
  `local_fallback`
- **AND** `local_ci_fallback.hosted_ci_status_claimed` is false

#### Scenario: local-ci fallback uses owner gates

- **WHEN** remote publication is unavailable or deferred
- **THEN** ETHOS recommends `tools/ci/scripts/run-local-ci.sh` as local
  fallback evidence
- **AND** that script invokes reusable owner gate scripts rather than restating
  hosted CI policy inline
- **AND** local fallback evidence does not claim hosted CI pipeline success

### Requirement: OpenSpec active carrier residue is visible across protected branch trees

ETHOS SHALL make active OpenSpec carriers visible when they remain in configured
protected branch Git trees. Current protected-role checkouts MUST block on active
carriers. Non-current protected branch residue MUST remain visible as an advisory
signal so stale protected refs can be repaired without misclassifying the current
accepted truth horizon.

#### Scenario: Current release root blocks active carrier residue

- **WHEN** repository audit runs on a checkout whose role is `release_root`
- **AND** `openspec/changes/<id>/` exists outside `archive/`
- **THEN** audit reports `openspec_active_change_unarchived:<id>:release_root` as a required gap

#### Scenario: Non-current protected branch residue is advisory

- **WHEN** repository audit runs on a different current role
- **AND** a configured protected branch tree contains `openspec/changes/<id>/` outside `archive/`
- **THEN** audit includes `openspec_protected_branch_active_change_unarchived:<branch>:<role>:<id>` in OpenSpec advisory gaps
- **AND** audit does not make the current checkout fail solely because of that non-current protected branch residue

### Requirement: Advisory governance signals are visible in reader views

ETHOS SHALL expose non-blocking advisory governance signals in report and orient
reader views without treating them as transition-blocking required gaps.

#### Scenario: Report exposes advisory signal count and layer

- **WHEN** `ethos report --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** when there are advisory gaps but no required gaps the report remains
  `ok=true` and reports `state=advisory` rather than `state=ready`
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Orient carries advisory readiness signals

- **WHEN** `ethos orient --json` runs with report payload available
- **THEN** orientation readiness includes advisory signal count and items
- **AND** the human orientation output can mention advisory signals without granting mutation authority

#### Scenario: Report exposes advisory signal count, layer, and bounded next actions

- **WHEN** `ethos report --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** `gap_layers.advisory_signals.next_actions` lists bounded inspection or explanation actions for known advisory signals
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Orient carries advisory readiness signals and actions

- **WHEN** `ethos orient --json` runs with report payload available
- **THEN** orientation readiness includes advisory signal count and items
- **AND** orientation readiness includes advisory next actions derived from report
- **AND** the human orientation output can mention advisory signals without granting mutation authority

#### Scenario: Report carries Work Lane coordination advisories

- **WHEN** `ethos report --json` runs and workspace status contains Work Lane coordination advisory gaps
- **THEN** the report summary includes those gaps in `advisory_gap_count`
- **AND** `gap_layers.advisory_signals.advisory_gaps` includes the Work Lane coordination advisories
- **AND** `gap_layers.advisory_signals.next_actions` routes to read-only coordination inspection commands
- **AND** top-level `next_actions` mirrors those advisory inspection commands when
  no blocking gap is present
- **AND** the advisories do not become report `required_gaps`

#### Scenario: Report carries Work Lane coordination blockers

- **WHEN** `ethos report --json` runs for a product or adopter profile and workspace status contains required Work Lane coordination gaps
- **THEN** those required coordination gaps appear in report `required_gaps`
- **AND** `gap_layers.coordination_risk.required_gaps` carries the required coordination gaps
- **AND** `gap_layers.coordination_risk.advisory_gaps` carries advisory coordination signals without making them required
- **AND** product and adopter profiles both surface required coordination gaps as blockers
- **AND** the scorecard remains read-only and does not authorize foreign Work Lane cleanup

### Requirement: Generated Evidence Boundary
ETHOS SHALL keep generated proof artifacts outside repository truth while making
latest-artifact writes deterministic enough for proof gates.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.

### Requirement: Forge provider projections preserve ETHOS repository truth

ETHOS SHALL support GitHub and GitLab as hosted forge providers that project the
same repository governance contract without changing `status -> plan -> prove ->
land -> publish` semantics.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** a repository enables both GitHub and GitLab provider profiles
- **THEN** provider templates SHALL invoke repository-owned gate scripts or
  `ethos ...` commands for the same required gate classes
- **AND** provider YAML drift SHALL be checkable from tracked template sources
- **AND** provider-specific syntax checks SHALL NOT be treated as repository
  proof by themselves.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a GitHub or GitLab provider projection is emulated locally
- **THEN** the evidence SHALL name the local emulator evidence class
- **AND** it SHALL record the provider, template or projection path, command,
  start and end Git head, dirty state, return code, and changed-scope summary
- **AND** it SHALL record whether the Git head stayed stable for the emulator run
- **AND** observation modes such as `doctor`, `list`, and `dry-run` MAY report a
  missing optional emulator binary as bounded local evidence with
  `tool_available=false` without claiming hosted provider status
- **AND** materializing emulator run modes SHALL fail closed when the required
  emulator binary is unavailable
- **AND** normal emulator run modes SHALL refuse untracked files by default
  because provider materialization can omit them
- **AND** it SHALL explicitly state that hosted provider status was not claimed.

### Requirement: Tool adoption remains profile and adapter scoped

ETHOS SHALL admit mature tooling through contracts, profiles, adapters,
projections, and gates instead of making adopter tools product ontology.

#### Scenario: Planned tools do not become active gates by catalog presence

- **WHEN** a tool is listed in `system/tools.toml` with `planned = true`
- **THEN** ETHOS SHALL NOT report it as an active quality floor
- **AND** activation SHALL require a config owner, reusable execution surface,
  CI or hook projection, and proof coverage.

#### Scenario: Optional method packs remain replaceable

- **WHEN** an agent uses Superpowers or another method pack to plan or review a
  change
- **THEN** the method pack MAY be recorded as execution context
- **AND** repository truth SHALL still require promoted source, docs, OpenSpec,
  claim, evidence, or command proof
- **AND** missing method-pack availability SHALL NOT block ETHOS repository
  governance when equivalent evidence discipline is satisfied.

### Requirement: OpenSpec customization stays official-compatible

ETHOS SHALL apply official OpenSpec validation before ETHOS-specific schema,
capability profile, claim binding, evidence, and archive lifecycle checks.

#### Scenario: ETHOS validates capability metadata after official OpenSpec

- **WHEN** an OpenSpec change or accepted spec is validated for ETHOS governance
- **THEN** official OpenSpec validation SHALL run first
- **AND** ETHOS SHALL validate repo-local capability profiles, proposal facets,
  claim carriers, evidence refs, and archive closeout without replacing official
  OpenSpec syntax or semantics.
