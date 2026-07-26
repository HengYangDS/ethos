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

### Requirement: Parity evidence is committed before Work Lane proof

ETHOS SHALL treat stale configured generic parity evidence as an explicit
evidence-freshness proof gap. A Work Lane that changes the parity-relevant tree
shall refresh and commit its parity evidence before it executes proof or lands.

#### Scenario: parity-relevant Work Lane source makes generic evidence stale

- **GIVEN** a Work Lane has committed a parity-relevant source or contract change
- **AND** its tracked generic parity evidence no longer matches the resulting
  parity-relevant semantic tree
- **WHEN** `ethos quality evidence-freshness --json` or executed proof evaluates
  the Work Lane
- **THEN** ETHOS reports the parity evidence invalidity as a required gap
- **AND** it returns the Work-Lane-owned parity refresh package
- **AND** it does not require a candidate or accepted root to write tracked evidence.

#### Scenario: evidence recording commit precedes proof and land

- **GIVEN** an admitted Work Lane refreshes generic parity evidence after its
  source commit
- **WHEN** it commits only the resulting evidence record and then executes proof
- **THEN** semantic-tree freshness accepts the evidence-recording commit
- **AND** the Work Lane may proceed to normal candidate landing
- **AND** candidate and accepted roots remain protected from direct parity writes.

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

ETHOS SHALL expose a release policy report covering version alignment, hosted
profile surfaces, protected branch/tag expectations, attestation formats,
publication topology, and the executable local verification/install owners
declared by that topology.

#### Scenario: Release policy is complete

- **WHEN** `ethos quality release-policy --json` runs in the ETHOS repository
- **THEN** the result reports no required gaps for release files, hosted profile
  templates, protected refs, version alignment, attestation formats,
  publication topology, and local command owners
- **AND** each declared local verification or installation command resolves to
  an executable regular file inside the governed repository.

#### Scenario: Phantom local owner blocks release readiness

- **WHEN** a declared local verification or installation command is absent,
  names a missing or non-regular file, or lacks an executable bit
- **THEN** release policy SHALL report a stable required gap for that field and
  path
- **AND** `ok` SHALL be false.

#### Scenario: Local owner cannot escape the repository

- **WHEN** a declared local command is absolute, contains a traversal that
  resolves outside the repository, or follows a link outside the repository
- **THEN** release policy SHALL report a path-escape required gap
- **AND** it SHALL NOT inspect or execute the outside target as a release owner.

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

#### Scenario: Reference storage maintenance cannot bypass accepted admission

- **GIVEN** Git's files ref backend can represent `pack-refs` with transactions
  indistinguishable from accepted branch creation or deletion
- **WHEN** `ethos hook install` arms the reference-transaction guard
- **THEN** it writes local `gc.packRefs=false` and blocks installation if that
  maintenance policy cannot be recorded
- **AND** the hook applies its existing fail-closed admission to every raw
  accepted transaction rather than guessing that a physical ref rewrite is safe
- **AND** a manual `pack-refs` is not classified as an authorized closeout.

### Requirement: OpenSpec Lifecycle Trust Review

ETHOS SHALL review OpenSpec lifecycle readiness in addition to official
OpenSpec CLI validation. An official `no-tasks` Change SHALL be treated as an
active, non-complete lifecycle carrier: it may bootstrap only its own absent
untracked `scope.toml` companion through the existing companion guard, but it
does not satisfy proposal, design, task, delta-spec, claim-binding, validation,
or proof requirements.

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

#### Scenario: Newly created official Change bootstraps its scope companion
- **GIVEN** the official OpenSpec CLI reports one Change as `no-tasks`
- **AND** that Change has no tracked or malformed `scope.toml` companion
- **WHEN** prewrite evaluates only that exact Change-local `scope.toml` path
- **THEN** it treats the Change as active and admits the existing exact-one
  scope-bootstrap path
- **AND** an ordinary material path remains blocked until the valid companion
  declares coverage
- **AND** an `in-progress` Change remains preferred over `no-tasks`, while an
  unknown official status remains excluded.

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

ETHOS SHALL provide one first-hour adopter path that is read-only unless apply
is explicitly authorized and exact-HEAD-bound, and that explains the one binding
carrier before mutation.

#### Scenario: Adoption dry-run is inspected

- **WHEN** `ethos adopt --json` runs
- **THEN** the result SHALL report read files, the exact one-file plan, apply
  criteria, conflicts, and rollback instructions
- **AND** profile selection, historical profile names, `init`, explicit
  `--dry-run`, and overlay SHALL not remain as alternate adoption paths.

#### Scenario: Adoption apply is authorized

- **WHEN** adoption is requested with `--apply`
- **THEN** mutation SHALL require `--authorize` and an exact matching
  `--expect-head`
- **AND** a missing repository, authorization, or HEAD match SHALL block before
  the binding is written.

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

#### Scenario: Sanctioned Work Lane replay binds its named ref

- **GIVEN** `ethos lane refresh-base --apply --authorize --expect-head <head>`
  is replaying a clean owned Work Lane onto the configured candidate branch
- **AND** Git temporarily detaches `HEAD` and creates a replay commit
- **WHEN** the commit-time fallback hook evaluates staged tracked paths from a
  validated Git rebase `head-name` naming that configured `work/*` branch
- **THEN** mutation admission retains detached `HEAD` as `current_head` for
  diagnosis
- **AND** it resolves the named Work Lane ref as `binding_head` for comparison
  with the lease's `expected_head`
- **AND** ordinary writes bind the lease to current `HEAD`
- **AND** missing named refs, mismatched lease heads, accepted, candidate,
  submit, other, and unknown detached branches remain protected and fail closed

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

#### Scenario: refresh-base merges independent source-budget debt additions

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replay conflicts only on `.ethos/rules.toml`
- **AND** both sides retain every base source-budget debt record byte-for-byte,
  preserve all content outside that debt section, and add only distinct valid
  debt record identifiers with non-negative allowances
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
  --json` runs
- **THEN** ETHOS writes the candidate-side record order followed by the Work Lane
  additions, recomputes `maximum_total`, and returns `state = "base_refreshed"`
- **AND** it reports `semantic_ledger_merged:source_budget_debt` without marking
  parity projection refresh as required
- **AND** duplicate additions, malformed records, changed base records, changed
  adjacent content, or any additional conflict path remain fail-closed

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
carries the deletion. Archive closeout SHALL reject non-canonical or duplicate
logical archive identities.

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

#### Scenario: Archive identity is canonical and unique

- **WHEN** archive closeout evaluates historical carriers
- **THEN** each name SHALL be `YYYY-MM-DD-<date-free-logical-id>`
- **AND** each logical ID SHALL resolve to exactly one archive carrier
- **AND** numeric-leading, terminal-date, and duplicate logical identities
  SHALL block closeout without compatibility aliases or date selection.

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

#### Scenario: Campaign closeout scopes one explicit campaign

- **GIVEN** more than one campaign manifest exists
- **WHEN** `ethos campaign closeout --campaign <campaign-id> --json` runs
- **THEN** the campaign package includes only the selected campaign
- **AND** the report records the requested selector
- **AND** unrelated campaign gaps do not become selected-campaign gaps.

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

ETHOS SHALL evaluate mutation-capable invocation as an action-specific request
over applicable Commitments, current repository facts, and bounded Evidence.
Authority SHALL rank truth sources rather than act as an identity or permission
engine. Intent and confirmation flags, holder labels, identity assertions, and
prior decisions SHALL NOT become reusable authorization by themselves.

#### Scenario: mutation decision is exact-request bound

- **WHEN** ETHOS evaluates a mutation request
- **THEN** it returns `allow`, `block`, or `defer` with `why`, `next`, and
  `required_gaps`
- **AND** the decision binds action, resource, expected mutable state, policy
  refs, evidence refs, and decision basis
- **AND** `allow` applies only to that request and mints no role, capability,
  session, token, or reusable authorization.

#### Scenario: confirmation and user instruction do not bypass policy

- **WHEN** a caller supplies `--apply`, legacy `--authorize`, another destructive
  confirmation, or an unverified session instruction
- **THEN** ETHOS treats it as execution intent or active-session reasoning input
- **AND** it is not caller authentication or durable repository policy
- **AND** any resulting waiver, exception, or policy change still becomes a
  bounded Commitment/Change and passes applicable mutation and transition
  controls.

#### Scenario: external identity remains bounded Evidence

- **WHEN** a Commitment requires organization or workload identity
- **THEN** an adapter verifies the minimum issuer-qualified identity reference,
  audience, method, validity, optional delegation, and attestation digest
- **AND** admission separately checks whether that attestation is sufficient for
  the exact action
- **AND** credentials, bearer tokens, unnecessary personal attributes, and a
  Principal, Agent, Session, Team, Party, or account registry remain outside
  repository truth.

#### Scenario: governance controls cannot approve themselves

- **GIVEN** a Change modifies authorization policy, identity trust, proof floors,
  admission code, owner scripts, schemas, or enforcement adapters
- **WHEN** ETHOS evaluates promotion
- **THEN** accepted incumbent controls run from incumbent or protected external
  provenance and candidate controls separately prove candidate conformance
- **AND** the decision binds both heads, control digests, and runner provenance
- **AND** unavailable incumbent provenance defers rather than trusts candidate
  controls
- **AND** first policy adoption requires a bootstrap approver/verifier configured
  outside the candidate tree and a bootstrap Chronicle decision.

### Requirement: Claim evidence freshness is explicit

ETHOS SHALL distinguish durable historical support from evidence that asserts
current repository state. Every active claim SHALL declare exactly one evidence
freshness mode: `historical`, `head_bound`, or `semantic_scope`.

#### Scenario: historical evidence is durable without pretending currentness

- **WHEN** an active claim declares `historical` freshness
- **THEN** ETHOS verifies its dated evidence digest and ordinary active-claim
  trust-envelope requirements
- **AND** it does not emit a missing-HEAD migration advisory
- **AND** it does not claim that historical evidence proves the current HEAD.

#### Scenario: currentness-sensitive evidence fails closed

- **WHEN** an active claim declares `head_bound` or `semantic_scope` freshness
- **THEN** ETHOS requires the binding fields of that mode
- **AND** a different declared HEAD blocks `head_bound` evidence
- **AND** a changed declared semantic target blocks `semantic_scope` evidence
- **AND** absent or unknown freshness mode is a required gap.

### Requirement: Work Lane Coordination Read Model

A Lane Lease SHALL remain ignored, one-writer coordination within one Git common
directory. It identifies one concrete holder and generation but grants no
identity, capability, filesystem fence, cross-host lock, or repository truth.
Reader output is a non-reusable action preview. Bounded readers SHALL preserve
`deferred`, even with no visible foreign lanes; only a fully computed foreign
inventory may report `exact`.

#### Scenario: foreign lane preview remains observe-only

- **WHEN** status or orientation reports a linked foreign Work Lane
- **THEN** its action preview lists `observe` as the only candidate action and
  blocks `write`, `land`, and `retire`
- **AND** it states `mints_authority=false` and `recheck_required=true`
- **AND** actual mutation re-evaluates the exact current request
- **AND** legacy actor-capability fields cannot be replayed as authority and are
  retired after client migration.

#### Scenario: bounded readers defer foreign path scopes

- **WHEN** a bounded status, planning, proof, landing, publication, or scorecard
  reader needs local state and aggregate lane signals but not a coordination
  inventory
- **THEN** ETHOS MAY defer foreign Work Lane path scopes instead of running one
  history diff per visible foreign lane
- **AND** each deferred lane remains explicitly marked `scope_state=deferred`
  while retaining its non-authoritative observe-only coordination state
- **AND** the reader preserves observable lane count and lease signals without
  inferring path overlap, branch relation, dirty foreign contents, or retirement
  readiness
- **AND** full `lane status` and mutation admission retain exact foreign path
  scope computation before making any coordination decision.

#### Scenario: projection preserves observed coordination detail state

- **WHEN** bounded status or orientation projects a coordination observation
- **THEN** its summary and coordination payload SHALL both expose
  `detail_state=deferred`
- **AND** counts requiring foreign-path inspection SHALL remain `null` even when
  no foreign Work Lane row is visible
- **AND** a full coordination inventory MAY expose `detail_state=exact` and
  integer detail counts only after computing that full inventory
- **AND** neither state grants foreign Work Lane mutation authority.
#### Scenario: bounded-reader regression debt is explicit and temporary

- **WHEN** the bounded status read model introduces a focused regression carrier
  before its full and bounded fixtures can share a smaller harness
- **THEN** any source-budget allowance names that exact carrier, owner,
  replacement, and deletion wave
- **AND** its allowance is limited to the measured temporary carrier cost
- **AND** the ledger's aggregate maximum equals the sum of its append-only
  records
- **AND** later fixture consolidation removes the allowance rather than making
  it permanent.

#### Scenario: normalized lease has one concrete current holder

- **WHEN** a lane lease is created, renewed, resumed, or handed off
- **THEN** it binds a random local lane-incarnation ID, lease ID, structured
  holder reference, epoch, issuance, renewal, expiry, and optional claim/scope
- **AND** one lane incarnation has at most one current writer holder
- **AND** renewal preserves holder, lease ID, and epoch while handoff changes
  holder and increments epoch
- **AND** the prior holder resumes an expired lease only with the old generation,
  unchanged expected head, and no contrary accepted judgment
- **AND** expiry, provider labels, missing state, or ambiguity never authorize
  another holder or cleanup.

#### Scenario: lease generation detects but does not claim hard fencing

- **WHEN** an invocation's expected holder, lease ID, epoch, or head is stale
- **THEN** normal ETHOS mutation paths reject or flag it
- **AND** handoff requires offer, acceptance, and holder quiescence
- **AND** ETHOS does not claim to stop an already-running or bypassing same-user
  filesystem process
- **AND** uncertainty or residue blocks integration until inspected.

#### Scenario: lease and Git lifecycle is crash-consistent

- **WHEN** a lane operation spanning Git, filesystem, and SQLite partially fails
- **THEN** ETHOS reports the exact repair-required state and verifies
  postconditions on idempotent retry
- **AND** normal authoring remains blocked until required Git and sole-lease
  postconditions hold
- **AND** ETHOS does not claim cross-store atomicity or silently choose among
  duplicate legacy leases.

#### Scenario: legacy adoption and cleanup resist replay

- **GIVEN** a legacy or recreated lane lacks trusted normalized state
- **WHEN** it is adopted or exceptionally cleaned
- **THEN** a provable current holder may normalize only that same holder/head
- **AND** other cases require an accepted maintainer decision pre-binding the
  exact target observation and a new local lane-incarnation ID
- **AND** cleanup binds that incarnation digest so a same-named branch or another
  clone cannot replay the decision
- **AND** missing legacy incarnation evidence blocks destructive cleanup rather
  than creating a global repository or Agent registry.

#### Scenario: cross-host handoff creates destination-local coordination

- **WHEN** work moves to another clone or Git common directory
- **THEN** transfer binds content-addressed Git state and a digest-bound context
  or recovery carrier, not the source SQLite lease
- **AND** dirty tracked/untracked work is committed or explicitly preserved, not
  stashed or left in chat
- **AND** the destination creates a new local lane and acknowledges it before the
  source revokes its writer lease or retires its observe-only copy
- **AND** neither side claims a distributed lease or shared session identity.

### Requirement: Repository Transition Decision Basis

ETHOS SHALL report enforcement boundary, identity basis, mutable-state bindings,
evidence boundary, verifier provenance, and time basis as orthogonal decision
facts rather than a scalar trust score. Strong claims SHALL be limited to the
truth horizon and enforcement coverage actually proved.

#### Scenario: local guards do not masquerade as hosted enforcement

- **WHEN** prewrite, local hooks, and current lease checks admit local work
- **THEN** the decision reports local-process enforcement and its exact state,
  identity, evidence, verifier, and time bases
- **AND** it does not claim hosted verification, adversarial isolation, or that a
  same-user bypass was impossible.

#### Scenario: prevention claim requires complete mediation

- **WHEN** ETHOS claims that a truth-horizon ref transition could not bypass
  admission
- **THEN** an enforcement receipt proves that the boundary mediated every
  relevant transition at that horizon
- **AND** a hook, CI file, or provider template alone proves configuration intent
  rather than live enforcement
- **AND** unknown or bypassable coverage makes no prevention claim.

#### Scenario: local accepted and remote publication remain distinct

- **WHEN** independent clones integrate or publish concurrent work
- **THEN** local candidate/accepted transitions bind state within their own Git
  common directory
- **AND** the remote old/new ref update is the shared cross-host publication
  horizon
- **AND** stale conflicts fail by expected-state comparison
- **AND** local readiness is not reported as remote publication or hosted proof.

#### Scenario: decision dimensions do not substitute for one another

- **WHEN** an action requires identity, state, freshness, verifier, or evidence
  obligations
- **THEN** every required dimension is independently satisfied
- **AND** strong identity does not repair stale proof, HEAD-bound proof does not
  identify a caller, and local time does not upgrade hosted evidence
- **AND** malformed or unverifiable time fails closed where freshness is required.

### Requirement: Work Lane Lifecycle Resolution

ETHOS SHALL keep routine mechanically determined lane lifecycle local and SHALL
record only exceptional interpretive judgments as evidence-bound Chronicle
`decision` events. Chronicle SHALL NOT become lease telemetry or a separate lane
resolution database.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and postcondition receipts
- **AND** no tracked Chronicle decision is required.

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** orphan recovery, foreign retirement, non-mechanical supersession,
  disputed handoff, preserve, block, or irreversible deletion is requested
- **THEN** a separate owned governance Work Lane has already promoted a
  Chronicle decision binding policy, evidence, exact head, lane-incarnation
  digest, disposition, recovery plan, and target-observation digest
- **AND** cleanup recomputes the mutable target facts before its first
  destructive step
- **AND** any mismatch blocks cleanup and requires a new decision
- **AND** the decision authorizes an effect while postconditions alone prove what
  was actually removed.

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** lane ownership, lease state, tracked/untracked contents, or recovery
  status is dirty, missing, ambiguous, or unknown
- **THEN** ETHOS preserves or blocks the lane instead of automatically deleting
  it
- **AND** irreversible deletion requires an accepted decision proving the exact
  target and why preservation is impossible or no longer required.

#### Scenario: break-glass reconciles after emergency action

- **GIVEN** a predeclared break-glass Commitment binds verified maintainer
  identity, exact target/head, reason, blast radius, expiry, preservation
  default, and postcondition plan
- **WHEN** an emergency command independently verifies those facts and acts
  before a new Chronicle decision can be promoted
- **THEN** it emits a digest-bound receipt and blocks later integration and
  publication
- **AND** a separate governance Work Lane promotes post-hoc judgment and
  reconciles residue before the block clears
- **AND** a self-supplied flag or holder string is insufficient.

#### Scenario: lane handoff is recorded as Chronicle resolution

- **GIVEN** a Work Lane handoff cannot be resolved by the normal local
  offer/accept protocol or becomes disputed
- **WHEN** an accepted exceptional judgment resolves the handoff
- **THEN** ETHOS records a Chronicle `decision` event binding the prior and next
  holder observations, evidence, exact head, lane-incarnation digest, and result
- **AND** routine local handoff remains ignored coordination and does not require
  tracked Chronicle telemetry
- **AND** the decision does not replace the active destination-local Lane Lease.

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has missing, stale, ambiguous, or legacy holder evidence
- **WHEN** ETHOS audits the lane for exceptional closeout or cleanup
- **THEN** orphan-like facts remain observations requiring a separate accepted
  resolution decision before destructive action
- **AND** the durable outcome records `retire`, `preserve`, `block`, `handoff`, or
  `break_glass` together with exact target and recovery evidence
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted.

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **GIVEN** one clean ownerless source Work Lane has diverged because its
  historical evidence and carrier bytes differ from an independently accepted
  current-baseline implementation of its useful behavior
- **AND** a target-specific accepted Claim and Chronicle bind its exact ref,
  exact source head, semantic basis, recovery plan, and `lane_resolution/retire`
  policy
- **WHEN** the native resolver records and applies a fresh decision for that
  exact linked source with break-glass and irreversible confirmation
- **THEN** it SHALL re-observe the source before effect and emit a receipt after
  the exact retirement
- **AND** tree inequality, a missing lease, a preservation package, or an
  inventory entry alone SHALL NOT authorize retirement
- **AND** the authority SHALL NOT extend to another lane, a valid lease, remote
  mutation, or a hosted-provider claim.

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
Generated proof artifacts SHALL remain outside repository truth, with
deterministic latest-artifact writes. Product and contributor package builds
SHALL clear and write `build/artifacts/python`, SHALL rely on the repository-level
ignore, and SHALL NOT use root `dist/` or add an output-local `.gitignore`.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.

#### Scenario: An interrupted coverage writer does not block future proof forever

- **GIVEN** the generated coverage writer lock records a process identity whose
  PID and start fingerprint no longer identify a live process
- **WHEN** a later Python owner test gate starts for that same evidence home
- **THEN** it reclaims only that dead-owner lock before acquiring the writer
  boundary
- **AND** it never preempts an unknown or live owner
- **AND** an unrecoverable lock fails after a configured bounded wait with the
  lock path and observed owner identity, rather than waiting indefinitely
- **AND** lock metadata remains ignored generated state, not repository truth.

#### Scenario: Package build writes to the semantic artifact home

- **WHEN** the product full proof executes its package build gate or a
  contributor follows the documented package-build command
- **THEN** `uv build --all-packages --out-dir build/artifacts/python --clear
  --no-create-gitignore` is the invoked command
- **AND** generated package artifacts remain disposable local state under
  `build/artifacts/python`
- **AND** concurrent workspace package builds do not race on an output-local
  ignore marker
- **AND** the invocation does not create or authorize repository-root `dist/`
  output.

### Requirement: Forge provider projections preserve ETHOS repository truth

GitHub and GitLab SHALL independently project the same `status -> plan -> prove
-> land -> publish` contract. Each has equal `repository`, `ci_cd`, and
`publication` capability; differing collaboration/distribution roles create no
precedence, failover, or replacement. Hosted CI accepts only `dev`, `main`, and
`submit/*`; `candidate/dev` and `work/*` remain local.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local candidate is excluded from hosted providers

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

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

### Requirement: Equal dual-remote publication topology

Publication SHALL comprise local verification/install plus independent GitLab
organization and GitHub public targets. The remotes have equal `repository`,
`ci_cd`, and `publication` capability and no authority ordering. Admission
permits only `dev`, `main`, and `submit/*`; local branches remain excluded.
`ethos publish` only observes targets. Compact declarations SHALL still accept
valid former verbose remote records.

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** pre-push admission receives a named declared target and `candidate/dev`
- **THEN** it SHALL reject the destination before proof admission
- **AND** it SHALL emit `publication_candidate_branch_remote_forbidden:candidate/dev`.

#### Scenario: independent remote observations remain no-push

- **WHEN** `ethos publish` observes GitLab and GitHub
- **THEN** it SHALL expose each target separately
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** hosted CI status SHALL remain unclaimed.

#### Scenario: valid verbose declaration remains accepted

- **WHEN** an adopter supplies valid `[[publication.remote]]` records
- **THEN** ETHOS SHALL resolve the same named GitLab and GitHub targets
- **AND** it SHALL retain equal capability and explicit-admission validation.

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

#### Scenario: clean ownerless landed residual retires after exact accepted absorption

- **GIVEN** one named linked Work Lane is clean, has no active lease, and its
  exact head is a strict ancestor of the current accepted branch
- **AND** an accepted target-specific Claim and Chronicle bind that source ref,
  source head, accepted absorption basis, and a recovery plan
- **WHEN** the native resolver records and applies a fresh
  `lane_resolution/retire` decision with break-glass and irreversible
  confirmation
- **THEN** it SHALL re-observe the named source's ref, head, linked binding,
  cleanliness, lease state, Chronicle bytes, and accepted control state before
  any effect
- **AND** it SHALL remove only that source's branch and worktree and write a
  receipt
- **AND** an inventory, expired lease, graph relation, or historical evidence
  alone SHALL NOT authorize retirement of another lane.

### Requirement: Work Lane Lifecycle Resolution

ETHOS SHALL keep routine mechanically determined lane lifecycle local and SHALL
record only exceptional interpretive judgments as evidence-bound Chronicle
`decision` events. Chronicle SHALL NOT become lease telemetry or a separate lane
resolution database.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and postcondition receipts
- **AND** no tracked Chronicle decision is required.

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** orphan recovery, foreign retirement, non-mechanical supersession,
  disputed handoff, preserve, block, or irreversible deletion is requested
- **THEN** a separate owned governance Work Lane has already promoted a
  Chronicle decision binding policy, evidence, exact head, lane-incarnation
  digest, disposition, recovery plan, and target-observation digest
- **AND** cleanup recomputes the mutable target facts before its first
  destructive step
- **AND** any mismatch blocks cleanup and requires a new decision
- **AND** the decision authorizes an effect while postconditions alone prove what
  was actually removed.

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** lane ownership, lease state, tracked/untracked contents, or recovery
  status is dirty, missing, ambiguous, or unknown
- **THEN** ETHOS preserves or blocks the lane instead of automatically deleting
  it
- **AND** irreversible deletion requires an accepted decision proving the exact
  target and why preservation is impossible or no longer required.

#### Scenario: break-glass reconciles after emergency action

- **GIVEN** a predeclared break-glass Commitment binds verified maintainer
  identity, exact target/head, reason, blast radius, expiry, preservation
  default, and postcondition plan
- **WHEN** an emergency command independently verifies those facts and acts
  before a new Chronicle decision can be promoted
- **THEN** it emits a digest-bound receipt and blocks later integration and
  publication
- **AND** a separate governance Work Lane promotes post-hoc judgment and
  reconciles residue before the block clears
- **AND** a self-supplied flag or holder string is insufficient.

#### Scenario: lane handoff is recorded as Chronicle resolution

- **GIVEN** a Work Lane handoff cannot be resolved by the normal local
  offer/accept protocol or becomes disputed
- **WHEN** an accepted exceptional judgment resolves the handoff
- **THEN** ETHOS records a Chronicle `decision` event binding the prior and next
  holder observations, evidence, exact head, lane-incarnation digest, and result
- **AND** routine local handoff remains ignored coordination and does not require
  tracked Chronicle telemetry
- **AND** the decision does not replace the active destination-local Lane Lease.

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has missing, stale, ambiguous, or legacy holder evidence
- **WHEN** ETHOS audits the lane for exceptional closeout or cleanup
- **THEN** orphan-like facts remain observations requiring a separate accepted
  resolution decision before destructive action
- **AND** the durable outcome records `retire`, `preserve`, `block`, `handoff`, or
  `break_glass` together with exact target and recovery evidence
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted.

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **GIVEN** one clean ownerless source Work Lane has diverged because its
  historical evidence and carrier bytes differ from an independently accepted
  current-baseline implementation of its useful behavior
- **AND** a target-specific accepted Claim and Chronicle bind its exact ref,
  exact source head, semantic basis, recovery plan, and `lane_resolution/retire`
  policy
- **WHEN** the native resolver records and applies a fresh decision for that
  exact linked source with break-glass and irreversible confirmation
- **THEN** it SHALL re-observe the source before effect and emit a receipt after
  the exact retirement
- **AND** tree inequality, a missing lease, a preservation package, or an
  inventory entry alone SHALL NOT authorize retirement
- **AND** the authority SHALL NOT extend to another lane, a valid lease, remote
  mutation, or a hosted-provider claim.

### Requirement: Preservation-bound exceptional Work Lane retirement

ETHOS SHALL offer an explicit `preserve-retire` exceptional disposition for a
dirty foreign or orphan Work Lane only after accepted Chronicle evidence has
bound the exact resolution.

#### Scenario: dirty residual lane is preserved without retirement

- **GIVEN** a linked Work Lane is dirty, missing a normalized lease, and its
  accepted Chronicle decision selects `lane_resolution/preserve`
- **WHEN** a maintainer records and applies the exact native two-phase decision
- **THEN** ETHOS recomputes the lane observation
- **AND** writes and verifies a digest-bound bundle, tracked patch, untracked
  archive when needed, and manifest
- **AND** retains the exact branch and linked worktree for later semantic replay
- **AND** emits a non-authoritative preservation receipt

#### Scenario: dirty lane is preserved before retirement

- **GIVEN** a linked Work Lane is dirty and its accepted Chronicle decision
  selects `lane_resolution/preserve-retire`
- **WHEN** a maintainer records a break-glass decision and applies it with an
  irreversible confirmation
- **THEN** ETHOS recomputes the exact lane observation
- **AND** writes a digest-bound bundle, tracked patch, untracked archive when
  needed, and manifest before removing the exact branch and linked worktree
- **AND** rejects the retirement if preservation is incomplete or stale
- **AND** emits a non-authoritative completion receipt with reconciliation
  required

#### Scenario: ordinary dirty retirement remains blocked

- **WHEN** a dirty Work Lane is resolved with plain `retire`
- **THEN** ETHOS reports `dirty_lane_retirement_blocked`
- **AND** it does not remove the branch or worktree

#### Scenario: Chronicle disposition is bound before the effect

- **GIVEN** an accepted Chronicle explicitly selects
  `lane_resolution/preserve`, `lane_resolution/retire`,
  `lane_resolution/preserve-retire`, or `lane_resolution/block` for one
  resolution class
- **WHEN** a maintainer records a native two-phase resolution decision
- **THEN** ETHOS binds the Chronicle path and SHA-256 digest together with the
  exact target observation digest
- **AND** native apply recomputes that observation before any effect
- **AND** a changed target blocks the decision rather than inheriting the prior
  disposition.

#### Scenario: detached dirty residue is normalized without changing bytes

- **GIVEN** one registered detached historical worktree has an absent Work Lane
  ref, no valid owner, a committed HEAD already in accepted history, and dirty
  tracked or untracked bytes
- **WHEN** a maintainer prepares it for target-specific behavioral resolution
- **THEN** the detached observation, reflog, HEAD, index, dirty inventory,
  content digests, session ownership, and path occupancy SHALL be captured first
- **AND** any reconstructed historical Work Lane ref SHALL point to the exact
  detached HEAD and SHALL NOT change index or working bytes
- **AND** ref reconstruction SHALL NOT mint ownership or effect authority
- **AND** an accepted target-specific Chronicle SHALL distinguish behavioral
  absorption, rejected historical behavior, preservation, retirement, and later
  package clearing before any destructive effect.

#### Scenario: expired dirty successor is semantically absorbed before closeout

- **GIVEN** a linked Work Lane has an expired or missing lease, no valid Claim,
  no process or open-file user, and dirty tracked or untracked bytes
- **AND** an accepted target-specific Chronicle binds its exact head, merge
  base, worktree registration, dirty paths, patch digest, and ownerless state
- **WHEN** current accepted source and tests prove every useful hunk exact or
  stronger, while rejected historical behavior is named explicitly
- **THEN** semantic absorption SHALL be distinct from byte preservation
- **AND** historical product code SHALL NOT be replayed merely to clean the lane
- **AND** native preserve-retire SHALL re-observe the complete source before
  preserving its exact bytes and removing only the named branch and worktree
- **AND** any newly valid owner, source drift, Chronicle drift, process
  occupancy, preservation failure, or accepted-basis drift SHALL block the
  effect
- **AND** recovery-package clear SHALL remain blocked until a separate accepted
  exact-manifest decision proves no unique behavior remains.

#### Scenario: overlapping valid-owner lanes remain protected

- **GIVEN** valid-owner foreign lanes overlap source or test paths mentioned by
  the ownerless semantic judgment
- **WHEN** the ownerless authority carrier is authored, proved, landed, or
  applied
- **THEN** visibility and overlap SHALL NOT authorize writes, tests, land,
  retirement, cleanup, or ownership transfer for those foreign lanes
- **AND** the effect SHALL be limited to the exact ownerless source named by the
  accepted Chronicle.

### Requirement: Durable exceptional-resolution recovery inventory

ETHOS SHALL materialize successful exceptional-resolution decisions, receipts,
preservation manifests, and bounded clear records under a stable local records
owner derived from the configured accepted checkout. The records owner SHALL
survive linked Work Lane retirement. Inventory and clear SHALL retain
read-only compatibility with legacy per-worktree lane-resolution artifacts,
but conflicting records for one decision SHALL fail closed.

#### Scenario: a preserved resolution is discoverable

- **GIVEN** a preserve or preserve-retire decision succeeds
- **WHEN** ETHOS completes the local effect
- **THEN** it writes a schema-validated immutable receipt bound to the observed
  lane, head, decision, and manifest when present
- **AND** inventory reports retained or unindexed state without minting
  authority from an artifact.

#### Scenario: a carrier invokes preservation and is later retired

- **GIVEN** a Work Lane invokes lane_resolution/preserve-retire for an exact
  source observation
- **WHEN** ETHOS writes the decision, package, and completion receipt
- **THEN** those records SHALL be owned by the configured accepted checkout's
  sibling recovery-records root rather than by the invoking Work Lane
- **AND** later retirement of the invoking Work Lane SHALL not remove them
- **AND** accepted-root inventory and package verification SHALL still report
  the retained package after both source and carrier worktrees are absent.

#### Scenario: immutable decision records cannot collide or redirect ownership

- **GIVEN** a caller records more than one decision for the same branch, or
  supplies a path that already exists
- **WHEN** ETHOS selects or writes the decision path
- **THEN** each default path SHALL be unique and an existing explicit path SHALL
  block with `lane_resolution_decision_path_exists`
- **AND** caller Work Lane policy bytes SHALL NOT redirect the configured
  accepted checkout's sibling records owner.

#### Scenario: a new decision path targets a legacy or unrelated root

- **GIVEN** a caller supplies an explicit decision path outside the configured
  accepted checkout's sibling lane-resolution records root
- **WHEN** ETHOS plans the decision
- **THEN** it SHALL report `lane_resolution_decision_path_not_local_artifact`
- **AND** it SHALL not write into a legacy, foreign-worktree, or unrelated root.

#### Scenario: a tampered decision identifier attempts package path escape

- **GIVEN** a stored decision identifier is not canonical
  `lane-decision:<UUID>` or its package realpath escapes the pinned records root
- **WHEN** ETHOS applies the decision
- **THEN** it SHALL block before package materialization
- **AND** it SHALL not write into a foreign, legacy, or unrelated root.

#### Scenario: an existing package directory cannot be reused

- **GIVEN** the canonical package path for one decision already exists
- **WHEN** ETHOS applies a preserve or preserve-retire decision
- **THEN** it SHALL report `lane_resolution_preservation_package_exists`
- **AND** it SHALL not overwrite any existing recovery bytes.

#### Scenario: a completion receipt is already present or reserved

- **GIVEN** the deterministic completion-receipt destination already exists or
  another conforming writer owns its hidden reservation sidecar
- **WHEN** ETHOS applies a preserve-retire decision
- **THEN** it SHALL report `lane_resolution_receipt_path_exists` before package,
  ref, or worktree mutation
- **AND** it SHALL preserve the existing bytes, branch, and linked worktree.

#### Scenario: receipt reservation follows the effect boundary

- **GIVEN** ETHOS exclusively reserves a completion-receipt destination
- **WHEN** preparation fails before effect or final receipt materialization
  succeeds
- **THEN** it SHALL release the reservation
- **AND** when a destructive effect completes but final receipt writing fails,
  it SHALL retain the reservation for reconciliation and still enforce the
  final writer's no-clobber check.

#### Scenario: a package or record path contains a symlink component

- **GIVEN** a package, manifest, receipt, or clear-record path redirects through
  a symlink
- **WHEN** ETHOS inventories, writes, verifies, or clears resolution records
- **THEN** it SHALL report `lane_resolution_package_path_unsafe` or
  `lane_resolution_record_path_unsafe`
- **AND** it SHALL not write or delete outside the pinned records owner.

#### Scenario: a legacy Work Lane still owns retained recovery material

- **GIVEN** a linked Work Lane contains an ignored legacy
  build/artifacts/lane-resolution/*/manifest.json
- **WHEN** ordinary landed or superseded retirement reobserves the selected
  worktree
- **THEN** ETHOS SHALL block with `lane_resolution_legacy_retention_present`
  before removing the worktree, branch ref, or lease
- **AND** it SHALL report that retained lane-resolution recovery material still
  requires migration or an evidence-bound clear.

#### Scenario: duplicate local decision records conflict

- **GIVEN** canonical and legacy stores expose the same decision ID with
  different manifest or receipt content
- **WHEN** inventory or clear is requested
- **THEN** ETHOS SHALL report `lane_resolution_decision_record_conflict`
- **AND** it SHALL not choose one record by scan order or remove either package.

#### Scenario: byte-identical package copies make clear ambiguous

- **GIVEN** more than one physical package location exposes the same decision ID
  and manifest bytes
- **WHEN** clear is requested
- **THEN** ETHOS SHALL report `lane_resolution_clear_package_ambiguous`
- **AND** it SHALL not remove only the scan-order-selected copy.

#### Scenario: durable manifest and receipt binding diverges

- **GIVEN** a retained manifest digest no longer matches its immutable receipt
- **WHEN** inventory, verification, or clear reads durable records
- **THEN** ETHOS SHALL report `lane_resolution_manifest_receipt_mismatch`
- **AND** it SHALL not report the package as consistently retained or cleared.

#### Scenario: final receipt materialization fails after effect

- **GIVEN** a stable decision and verified preservation package exist
- **WHEN** the bounded source transition completes but immutable receipt writing
  fails
- **THEN** ETHOS SHALL report `ok=false`, `state=partial_transition`, and
  `lane_resolution_receipt_write_failed_after_effect`
- **AND** the stable decision and package SHALL remain inspectable for
  reconciliation
- **AND** the exclusive receipt reservation SHALL remain present for explicit
  reconciliation
- **AND** the command SHALL not report ordinary success.

#### Scenario: one absorbed detached-residue package is cleared by exact manifest

- **GIVEN** an accepted Chronicle selects
  `lane_resolution/clear-preservation` for one exact decision id and manifest
- **AND** the retained tracked patch matches the pre-effect capture, the index
  patch is empty, no untracked archive exists, and accepted behavior contains
  no missing capability from that package
- **WHEN** a maintainer invokes native clear with the matching manifest,
  non-empty reason, break-glass, and irreversible confirmation
- **THEN** ETHOS SHALL re-read inventory and manifest bytes before removing only
  that package and emitting a clear receipt
- **AND** the original decision and completion receipt SHALL remain
- **AND** another package, a changed manifest, raw deletion, or batch clear
  SHALL remain blocked.

#### Scenario: one absorbed snapshot-replay package is cleared by exact manifest

- **GIVEN** an accepted Chronicle selects
  `lane_resolution/clear-preservation` for one exact decision id and manifest
- **AND** the native tracked patch reconstructs the pre-effect full-index dirty
  tree, the index patch is empty, no untracked archive exists, and accepted
  behavior contains no missing capability from that package
- **WHEN** a maintainer invokes native clear with the matching manifest,
  non-empty reason, break-glass, and irreversible confirmation
- **THEN** ETHOS SHALL re-read inventory and manifest bytes before removing only
  that package and emitting a clear receipt
- **AND** the original decision and completion receipt SHALL remain
- **AND** another package, a changed manifest, raw deletion, batch clear, or
  source reconstruction SHALL remain blocked.

### Requirement: Evidence-bound preservation-package clearing

ETHOS SHALL remove a retained recovery package only after a manifest-bound,
Chronicle-gated manual-clear decision.

#### Scenario: a package is cleared deliberately

- **GIVEN** the selected manifest matches its expected SHA-256 and the accepted
  Chronicle selects `lane_resolution/clear-preservation`
- **WHEN** a maintainer supplies a reason, break-glass, and irreversible
  confirmation
- **THEN** ETHOS records a clear receipt and removes only that package
- **AND** preserves the original resolution receipt and Chronicle

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL return a runner bootstrap for a newly started Work Lane that
executes its own source with uv state in semantic runtime homes.

#### Scenario: a Work Lane uses its bootstrap runner

- **WHEN** the operator runs the returned runner from the linked Work Lane
- **THEN** the uv environment is under `build/runtime/venv`
- **AND** the uv cache is under `build/runtime/tool-cache/uv`
- **AND** the command runner binds to that Work Lane source

### Requirement: Deterministic Official OpenSpec Tool Supply

ETHOS SHALL invoke the official `@fission-ai/openspec@1.6.0` package from its
repository-owned npx fallback and CI bootstrap while preserving explicit binary,
cached official CLI, and PATH precedence. Adoption SHALL NOT generate an
OpenSpec workspace or provider CI surface.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter and CI bootstrap
- **THEN** each repository-owned package invocation SHALL identify
  `@fission-ai/openspec@1.6.0`
- **AND** strict official OpenSpec validation SHALL remain the governance gate
- **AND** adoption SHALL plan no OpenSpec or CI carrier.

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

Campaign step legality SHALL derive from declared state, OpenSpec carrier, and
closeout. `active`/`in_progress` uses an active carrier and no terminal closeout;
`archived`/`landed` uses an archived carrier with non-terminal closeout;
`closed`/`retired` adds terminal closeout, accepted/candidate heads, and dated
evidence. A campaign may be active with only a planned next step, which readers
SHALL expose without inventing an active lane.

#### Scenario: archived carrier is presented as active

- **WHEN** campaign validation reads an `active` or `in_progress` step whose only
  carrier is under `openspec/changes/archive`
- **THEN** it reports a required
  `campaign_step_active_openspec_archived:<campaign>:<step>` gap
- **AND** it does not treat the campaign topology as a valid active lane.

#### Scenario: archived carrier awaits land

- **GIVEN** the official OpenSpec archive operation has moved the current Change
  under `openspec/changes/archive`
- **WHEN** its Campaign step declares `state = "archived"` with non-terminal
  closeout
- **THEN** Campaign validation SHALL accept the truthful archive-before-land
  intermediate state
- **AND** the step SHALL remain non-terminal until candidate and accepted
  closeout facts exist.

#### Scenario: pre-land state still references an active carrier

- **WHEN** an `archived` or `landed` step still resolves only under
  `openspec/changes/<id>`
- **THEN** Campaign validation SHALL report
  `campaign_step_preland_openspec_not_archived:<campaign>:<step>`.

#### Scenario: terminal step lacks archived carrier

- **WHEN** campaign validation reads a `closed` or `retired` step whose carrier
  remains only under `openspec/changes/<id>`
- **THEN** it reports a required
  `campaign_step_terminal_openspec_not_archived:<campaign>:<step>` gap.

#### Scenario: campaign awaits a planned successor

- **WHEN** every completed predecessor has terminal closeout and the immediate
  successor remains `planned`
- **THEN** campaign validation SHALL accept the absence of an active execution
  step
- **AND** `lane_topology.next_planned_step` SHALL identify that successor
- **AND** no active Work Lane SHALL be inferred until its carrier and lane exist.

### Requirement: Entrypoint audits distinguish declarations from producers

The generated-artifact entrypoint audit SHALL evaluate executable producer commands and SHALL NOT treat declarative cleanup, ignore, exclude, or forbidden-path configuration as evidence that the entrypoint produces generated state in a denied home.

#### Scenario: Structured manifest declares cleanup and ignore paths

- **WHEN** `pyproject.toml` contains denied-home tokens only in cleanup paths, ignore globs, exclusion lists, or local-state declarations
- **THEN** the entrypoint audit reports no producer gap for those declarations
- **AND** the denied path topology remains enforced if matching generated files actually exist

#### Scenario: Structured manifest task writes to a denied home

- **WHEN** a supported task command in `pyproject.toml` actively writes a cache or package artifact to a denied home
- **THEN** the entrypoint audit emits the corresponding denied-home producer gap
- **AND** declaration-only filtering does not suppress the finding

### Requirement: Worktree-bound semantic runtime bootstrap

One repository bootstrap SHALL bind `UV_PROJECT_ENVIRONMENT` to the current
worktree's `build/runtime/venv` and execute that checkout's source. Explicit
cache roots win; otherwise downloads use a host-scoped content-addressed cache.
Nested cross-worktree bootstrap SHALL use a bounded child cache namespace and
keep child source without waiting on the outer lock.
`ETHOS_RUNTIME_BOOTSTRAPPED=1` owner scripts SHALL invoke outer uv with
`--no-sync`. When that marker is already set and the request names the current
worktree's executable semantic Python with a valid `pyvenv.cfg`, the bootstrap
SHALL execute the original Python request directly without `uv sync` or a
nested `uv run`; it MUST NOT require an inherited runtime root to equal the
current worktree.

#### Scenario: two Work Lanes initialize independently

- **GIVEN** two linked Work Lanes from the same Git common directory
- **WHEN** each runs a Python owner command through the bootstrap
- **THEN** each command receives its own `<worktree>/build/runtime/venv`
- **AND** neither command resolves `<worktree>/.venv` as its project environment
- **AND** the cache location does not become a Work Lane lease, source, evidence,
  or authority store

#### Scenario: a hook starts before its checkout environment exists

- **GIVEN** a hook requests the default
  `<worktree>/build/runtime/venv/bin/python` and that interpreter is absent
- **WHEN** the request passes through the runtime bootstrap
- **THEN** the bootstrap invokes `uv run --group dev python` with the original
  Python arguments and lets uv materialize only that checkout's environment
- **AND** it does not resolve `<worktree>/.venv/bin/python`

#### Scenario: a nested hook bootstrap avoids parent cache-lock reentry

- **GIVEN** an outer uv command holds the selected cache lock for one worktree
- **WHEN** a Git hook in a different worktree requests its missing default
  semantic interpreter through the bootstrap
- **THEN** the hook materializes only the child worktree's
  `build/runtime/venv`
- **AND** its uv invocation uses a bounded namespace beneath the selected host
  or CI cache root
- **AND** it does not wait on or share the outer uv cache lock

#### Scenario: a marked owner script does not reenter its own environment lock

- **GIVEN** a product owner script is handed off through
  `env ETHOS_RUNTIME_BOOTSTRAPPED=1 <script>`
- **WHEN** the runtime bootstrap launches that handoff
- **THEN** its outer `uv run` invocation includes `--no-sync`
- **AND** the script retains ownership of any later tool synchronization
- **AND** an inner tool invocation does not wait on a parent process holding
  the same `<worktree>/build/runtime/venv` lock

#### Scenario: marked semantic Python bypasses nested synchronization

- **GIVEN** a hook or owner process has `ETHOS_RUNTIME_BOOTSTRAPPED=1`
- **AND** it requests the current worktree's executable
  `build/runtime/venv/bin/python` with a valid `pyvenv.cfg`
- **AND** an inherited runtime root may name a different outer worktree
- **WHEN** the runtime bootstrap dispatches that semantic Python request
- **THEN** it executes the original request directly
- **AND** it does not invoke `uv sync` or a nested `uv run`
- **AND** an unmarked, unavailable, invalid, or non-semantic request retains
  its existing runtime-bootstrap behavior

### Requirement: Explicit execution overrides remain bounded

ETHOS SHALL permit an explicit `ETHOS_PYTHON`, `PYTHON`, `UV_CACHE_DIR`, or
`ETHOS_UV_CACHE_DIR` override for a bounded invocation. An override MUST NOT
change the checkout root, substitute another checkout's source environment, or
silently make root `.venv` the default runtime.

#### Scenario: CI supplies its own cache path

- **GIVEN** a hosted CI projection supplies an explicit uv cache location
- **WHEN** an owner script invokes the runtime bootstrap
- **THEN** the bootstrap preserves that cache location
- **AND** the source environment remains under the current checkout's
  `build/runtime/venv`

### Requirement: Generated Artifact Topology Contract

ETHOS SHALL classify generated outputs by lifecycle and audit both files and
executable producers. Root `.venv` SHALL NOT serve normal execution; ignored
legacy copies may remain observable migration residue but SHALL NOT be
auto-deleted. Allowlisted host-bootstrap adapters may use the host interpreter
only to install or configure a missing hosted toolchain before repository
runtime exists, and SHALL NOT execute product modules.

#### Scenario: an executable entrypoint attempts root environment fallback

- **WHEN** generated-artifact topology audits a product-owned executable script,
  hook, or CI projection containing an active root `.venv/bin/python` fallback
  or bare `uv run` path that bypasses the semantic bootstrap
- **THEN** the audit reports a required runtime-entrypoint routing gap
- **AND** proof remains blocked until the producer routes through the bootstrap

#### Scenario: legacy root environment remains observable but non-authoritative

- **GIVEN** an ignored root `.venv` exists after the runtime contract changes
- **WHEN** topology and local-state audits run
- **THEN** they identify it as migration residue rather than product truth
- **AND** no cleanup command removes it without an explicit local operator action

### Requirement: Temporary test probe provenance remains explicit and bounded

ETHOS SHALL classify a dirty entry as a temporary test probe only when Git
reports it as untracked, its repository-relative path is under `tests/`, its
basename matches `test_*.py`, and its bounded file header contains the literal
`TEMP PROBE`. Workspace status SHALL expose a `temporary_probes` summary with
an exact count, a bounded list of repository-relative paths, and an overflow
indicator. The summary SHALL be present for clean, dirty, unavailable, and
non-Git provenance payloads.

#### Scenario: Explicit untracked probe is recognized

- **WHEN** an accepted or candidate checkout contains an untracked
  `tests/**/test_*.py` file whose header contains `TEMP PROBE`
- **THEN** workspace status includes that file in `dirty_provenance.temporary_probes`
- **AND** the summary count and path list identify the probe without changing
  the Git dirty entries

#### Scenario: Ordinary untracked files are not misclassified

- **WHEN** a dirty checkout contains an untracked file outside `tests/`, a
  non-test Python file, or a test file without the header marker
- **THEN** its ordinary dirty provenance remains visible
- **AND** `temporary_probes` does not classify that file as a probe

#### Scenario: Probe list remains bounded

- **WHEN** more temporary probes exist than the path-list bound
- **THEN** the summary reports the exact total count
- **AND** it reports a bounded repository-relative path list and an overflow
  indicator

### Requirement: Protected-root probe remediation is reader-only

ETHOS SHALL derive explicit temporary-probe remediation in orientation when an
accepted or candidate root has one or more classified temporary probes. The
JSON and human orientation views SHALL state that the operator must remove the
probe or migrate it into an owned Work Lane, and SHALL state that no automated
cleanup occurs. The projection SHALL NOT mint authority to write, land,
retire, or clean another lane.

#### Scenario: Accepted root receives explicit remediation

- **WHEN** `ethos orient --json` reads an accepted root with classified
  temporary probes
- **THEN** its candidate action names temporary-probe removal or migration
- **AND** its reason and next actions identify removal or migration into an
  owned Work Lane
- **AND** its mutation and landing capabilities remain false

#### Scenario: Ordinary dirty state keeps its existing orientation

- **WHEN** a protected root is dirty but has no classified temporary probe
- **THEN** orientation retains the generic dirty-state candidate action and
  remediation
- **AND** no temporary-probe remediation is implied

### Requirement: Independent verification is an optional action-scoped adapter

ETHOS SHALL default independent verification to disabled and SHALL allow an
adopter to select optional or required depth for an individual transition
action without declaring provider identities in repository truth.

#### Scenario: A repository does not opt in

- **WHEN** no independent-verification policy is declared
- **THEN** ETHOS SHALL retain local-first readiness semantics
- **AND** SHALL NOT require a provider account, network, key, anchor, or receipt.

#### Scenario: Publish requires independent re-execution

- **WHEN** an adopter declares required independent verification for `publish`
- **THEN** `ethos publish` SHALL block without a valid exact receipt
- **AND** SHALL NOT make that policy an admission requirement for another action.

### Requirement: Receipts are exact bounded evidence

ETHOS SHALL admit an independent receipt only when its protected provider
configuration and signature validate and its remote, commit, tree, action,
proof floor, policy digest, and implementation digest match the request.

#### Scenario: Receipt is valid but not semantic proof

- **WHEN** an exact independent receipt is admitted
- **THEN** ETHOS SHALL project `independently_reexecuted`
- **AND** SHALL NOT claim semantic correctness or mint authority.

### Requirement: Semantic claim attestations are typed and candidate-external

ETHOS SHALL treat `semantic_attested` as a distinct claim-assurance class only
when a typed candidate-external receipt binds the exact claim, dated evidence,
promotion-target semantic scope, and current HEAD. The receipt SHALL not mint
authority. Historical or ordinary digest-bound claims SHALL remain portable
without a receipt provider.

#### Scenario: A semantic attestation receipt matches the active claim

- **WHEN** an active `semantic_attested` claim is evaluated
- **THEN** ETHOS SHALL validate the receipt schema, canonical payload digest,
  reviewer role, basis, allow verdict, validity interval, receipt digest, claim
  id, dated-evidence digest, semantic scope digest, and current HEAD
- **AND** it SHALL reject a receipt stored inside the governed repository
- **AND** it SHALL expose only an `attested` non-authorizing trust-envelope state

#### Scenario: Existing labels lack a receipt

- **WHEN** a legacy `semantic` or unreceipted `semantic_attested` claim is
  migrated
- **THEN** it SHALL be represented as `digest_only`
- **AND** its summary and binding SHALL not claim semantic verification

### Requirement: Fresh Work Lane bootstrap avoids unnecessary runtime admission

ETHOS SHALL allow Git to create or reassert a fresh Work Lane ref without
materializing a checkout-local Python runtime when the ref does not change.
This exception SHALL be limited to a `work/*` branch with an absent selected
local runtime and either a zero old object ID or equal old and new object IDs.

#### Scenario: Fresh Work Lane ref is reasserted without a runtime

- **GIVEN** Git is creating a linked Work Lane checkout
- **AND** the reference-transaction event creates the Work Lane ref from the
  zero object ID or reasserts equal old and new object IDs
- **AND** the checkout-local runtime interpreter is absent
- **WHEN** the reference-transaction hook evaluates that event
- **THEN** it completes the non-accepted no-op event without invoking runtime
  materialization
- **AND** `ethos lane start --apply` can create the Work Lane and then acquire
  its lease without requiring network access.

#### Scenario: Protected and changed refs retain ordinary admission

- **WHEN** the reference-transaction event targets the accepted branch,
  changes an existing Work Lane ref, or targets a non-Work-Lane branch
- **THEN** ETHOS SHALL retain the existing runtime-backed admission path
- **AND** accepted-root admission remains fail-closed
- **AND** a committed changed Work Lane ref retains lease-head repair.

### Requirement: Work Lane refresh success is ancestry-bound

ETHOS SHALL report a successful Work Lane base refresh only when the candidate
HEAD captured before replay is an ancestor of the reported refreshed Work Lane
HEAD.

#### Scenario: zero-code replay leaves the Work Lane unrefreshed

- **GIVEN** a clean owned Work Lane is stale behind the configured candidate
  branch
- **AND** the replay subprocess returns zero without making the captured
  candidate HEAD an ancestor of the Work Lane HEAD
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
  --json` evaluates the replay result
- **THEN** ETHOS reports `state=blocked`
- **AND** it reports `refresh_base_postcondition_failed`
- **AND** it does not report `base_refreshed` or offer landing as the next
  lifecycle transition.

#### Scenario: parity-projection recovery preserves the same success condition

- **GIVEN** a stale Work Lane replays through admitted parity-projection
  recovery
- **WHEN** recovery reaches a terminal refreshed HEAD
- **THEN** ETHOS verifies the captured candidate HEAD is its ancestor before
  reporting `base_refreshed_projection_stale`
- **AND** it blocks with `refresh_base_postcondition_failed` if that fact is
  absent.

### Requirement: Canonical Persisted Claim Envelope

ETHOS SHALL load every tracked claim under the configured claims root from the
canonical claim envelope containing `[claim]` and `[evidence]`. Historical
records SHALL preserve dated evidence through an explicit freshness mode; a
reader SHALL NOT retain a second top-level change-claim parser or silently
upgrade an undeclared shape at runtime.

#### Scenario: Canonical historical claim is read

- **WHEN** a tracked claim declares canonical claim and evidence sections with
  a valid dated-evidence digest and `mode = "historical"`
- **THEN** ETHOS SHALL report the claim under its declared id
- **AND** ETHOS SHALL verify the dated-evidence digest without requiring its
  historical source head to equal the current head.

#### Scenario: Top-level legacy claim shape is encountered

- **WHEN** a tracked TOML file in the configured claims root lacks a `[claim]`
  envelope
- **THEN** ETHOS SHALL emit `<file-stem>:claim_envelope_missing` as a required
  gap
- **AND** ETHOS SHALL NOT interpret top-level lifecycle, evidence-reference, or
  promotion-target fields as a compatibility format.

### Requirement: Official OpenSpec goal metadata is lifecycle-compatible

ETHOS SHALL accept the official OpenSpec 1.6 `goal` field in active and archived
`.openspec.yaml` metadata while continuing to reject unrecognized metadata
keys.

#### Scenario: Official change creation supplies a goal

- **WHEN** an OpenSpec change metadata file contains `schema`, `created`, and
  an official `goal`
- **THEN** ETHOS metadata compatibility and archive closeout SHALL not report a
  metadata-key gap for `goal`
- **AND** an unknown key such as `owner` SHALL remain a required compatibility
  gap.

### Requirement: Canonical declarations have a self-contained package projection

ETHOS SHALL package canonical system declarations without making a wheel build
depend on paths outside its source distribution.

#### Scenario: The core wheel is built from its source distribution

- **WHEN** the `ethos-core` source distribution is unpacked for a wheel build
- **THEN** each packaged declaration is read from the sdist-local
  `src/ethos_core/data/` projection
- **AND** the wheel contains the corresponding `ethos_core/data/` resource
- **AND** the build does not require checkout-relative `system/` paths.

### Requirement: External-adopter profile evidence has a bounded durable record

ETHOS SHALL record a completed local external-adopter binding exercise through
a dated Chronicle and claim that bind the observed product revision, adopter
revision, binding outcome, and raw-bundle digest without promoting host-local
raw material or provider state into repository truth.

#### Scenario: Local profile evidence is promoted

- **WHEN** an isolated external-adopter binding exercise completes
- **THEN** its claim SHALL bind a dated Chronicle and SHA-256 raw-bundle identity
- **AND** the Chronicle SHALL record exact binding and conflict outcomes
- **AND** it SHALL state whether remote publication was performed.

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** the claim uses digest-only verification
- **THEN** it SHALL NOT claim semantic correctness, hosted-provider execution,
  provider authority, or independent review
- **AND** it SHALL NOT require a named local account, credential, key, daemon,
  or network service.

### Requirement: Bounded landed Work Lane retirement tolerates unrelated missing paths

ETHOS SHALL scope `ethos lane retire landed --branch <branch>` inspection to
the requested Work Lane before performing lane-local Git status checks. An
unavailable selected worktree path SHALL fail closed as non-retireable and
SHALL NOT raise an unhandled exception, delete a ref, or mutate any unrelated
Work Lane.

#### Scenario: Foreign historical worktree is unavailable

- **GIVEN** an unrelated foreign Work Lane remains registered with a missing
  filesystem path
- **WHEN** the matching owner retires a different clean, merged Work Lane by
  explicit branch and expected head
- **THEN** ETHOS evaluates and retires only the selected Work Lane
- **AND THEN** the unavailable foreign Work Lane remains untouched.

#### Scenario: Selected worktree is unavailable

- **WHEN** landed retirement selects a Work Lane whose path is unavailable
- **THEN** ETHOS returns a blocked non-retireable result for that lane
- **AND THEN** it does not delete the selected ref or any linked worktree.

### Requirement: Universal adopter OpenSpec lifecycle

ETHOS SHALL evaluate official OpenSpec lifecycle during plan and proof for every
governed root, including a valid adopter profile. Lifecycle gaps SHALL remain
OpenSpec/repository-governance gaps and SHALL NOT be represented as
`code_correctness_gates` or method-package authority.

#### Scenario: Valid adopter has an invalid Change lifecycle
- **WHEN** the adopter runs plan or prove
- **THEN** the lifecycle payload and its required gap are returned
- **AND** the command is not clean merely because the root is not the product.

### Requirement: Publish readiness distinguishes observed remote synchronization from execution

`ethos publish` SHALL keep local readiness, remote observation, remote mutation,
and hosted CI as separate evidence classes.

#### Scenario: Synchronized tracking ref is reported without a new push

- **WHEN** `ethos publish --probe-remote --json` observes the local tracking ref
  for the current branch at the same HEAD as the checkout
- **THEN** `summary.remote_publication_state` and
  `data.publication.remote_state` SHALL be `synchronized`
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** the mutation verdict SHALL remain `defer`
- **AND** the next action SHALL state that no push was performed

#### Scenario: Reachable but non-synchronized remote remains deferred

- **WHEN** the remote is available but the tracking comparison is not
  `synchronized`
- **THEN** `data.publication.remote_state` SHALL remain `deferred`
- **AND** the command SHALL not claim a remote push or hosted-CI result

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require every valid adopter declaration to carry a non-empty
`[openspec].material_paths` list. For changed paths matching that declaration,
prewrite, changed planning, and proof SHALL use the same selected-Change companion model.
Adoption SHALL emit the complete declaration; no historical profile-write exception remains.
Completed archive companions MAY participate only when their archive is in
current Work Lane scope.

#### Scenario: covered material path is admitted across all surfaces

- **GIVEN** a material path is covered by a valid selected Change companion
- **WHEN** prewrite, changed planning, or proof evaluates that path
- **THEN** the scope binding reports the same coverage fact
- **AND THEN** no material-scope required gap is produced.

#### Scenario: uncovered material path is rejected consistently

- **GIVEN** a declared material path lacks coverage by every valid selected
  companion
- **WHEN** any of prewrite, changed planning, or proof evaluates it
- **THEN** it SHALL report `openspec_material_path_uncovered:<path>`
- **AND THEN** it SHALL not substitute a proof gate, private schema, or method
  package for Change authority.

#### Scenario: incomplete unrelated companions remain diagnostic

- **GIVEN** one official active or archiving Change has a missing or invalid
  companion and another selected Change has a valid matching companion
- **WHEN** a material path covered by the valid companion is evaluated
- **THEN** the path is covered
- **AND** incomplete companion details remain advisory diagnostics rather than
  a global coverage gap.

#### Scenario: declaration and bootstrap fail closed

- **WHEN** an adopter omits, empties, or invalidates `material_paths`
- **THEN** ETHOS SHALL report a material-path declaration gap
- **AND WHEN** an official new Change needs its absent companion created
- **THEN** prewrite MAY admit only that exact untracked Change-local
  `scope.toml` path
- **AND THEN** the completed companion SHALL be syntactically valid, cover
  itself, and cover later material writes.

#### Scenario: existing adopter cannot bootstrap a missing declaration

- **WHEN** a tracked adopter profile lacks `material_paths`
- **THEN** ETHOS SHALL block the write
- **AND** it SHALL NOT emit `profile_material_paths_bootstrap` or admit a second
  profile-write path.

#### Scenario: final archive reconciliation remains covered

- **GIVEN** a completed Change is archived in the current Work Lane change
  scope and its archive has a valid `scope.toml`
- **WHEN** prewrite, changed planning, or proof evaluates a material path from
  that same current scope
- **THEN** the archive companion may cover declared matching paths
- **AND THEN** it SHALL cover paths inside that selected archive directory,
  including the companion itself, only for this reconciliation
- **AND THEN** it SHALL not cover a path outside that archive unless the
  companion explicitly matches it
- **AND** the same scope verdict is returned on all three surfaces.

#### Scenario: historical archive cannot authorize unrelated material work

- **GIVEN** an archive has a valid `scope.toml` but no file from that archive is
  in the current Work Lane change scope
- **WHEN** prewrite, changed planning, or proof evaluates a matching material
  path
- **THEN** the archive is excluded from scope coverage
- **AND** an uncovered path emits `openspec_material_path_uncovered:<path>`.

#### Scenario: archive companion diagnostics remain carrier-invalid

- **GIVEN** a current archive companion is missing or malformed
- **WHEN** lifecycle scope reports its diagnostic
- **THEN** the emitted diagnostic SHALL reduce to the shared carrier-invalid
  invalid-state category
- **AND** it SHALL not grant material-path coverage.

### Requirement: Accepted closeout remains candidate-first and non-self-approving

Accepted advance SHALL fast-forward to live candidate with candidate proof and
one-shot official closeout. Candidate-tree policy decides admission; accepted
hooks and CAS enforce it. With `release_mirror = "accepted_ff"`, both protected
refs advance atomically under that evaluator. A candidate replacement for the
reference-transaction hook SHALL be clean, executable, and transaction-local;
it SHALL NOT change global config or weaken raw admission. Otherwise configured
hooks remain.

#### Scenario: raw update-ref targets a proven candidate head

- **GIVEN** the candidate checkout is clean and has a complete proof for its
  live head
- **WHEN** a caller runs raw `git update-ref` to move the accepted branch to
  that head without official closeout intent
- **THEN** the accepted-ref hook SHALL reject the move
- **AND** candidate-tree evaluation SHALL not make the marker optional.

#### Scenario: Official accepted_ff closeout advances both protected refs

- **GIVEN** `dev` and `main` are atomically advanced by an official
  `accepted_ff` closeout to the live, proven candidate head
- **AND** the incumbent accepted checkout cannot run its hook reducer
- **WHEN** the armed reference-transaction hook prepares the transaction
- **THEN** it evaluates both transitions through the clean candidate runner
- **AND** it admits the transaction only when each exact closeout intent and
  substantive candidate/proof check passes
- **AND** `dev` and `main` reach the same candidate head atomically.

#### Scenario: Raw accepted or release-mirror move remains blocked

- **GIVEN** an `accepted_ff` repository has a proven live candidate head
- **WHEN** raw Git attempts to move `dev` or `main` without its exact
  closeout-intent marker
- **THEN** the armed hook blocks that transition
- **AND** no protected ref advances.

#### Scenario: Candidate hook replaces a legacy accepted hook

- **GIVEN** the accepted checkout has a legacy reference-transaction hook that
  rejects an accepted_ff release-mirror transition
- **AND** the clean candidate checkout at the proposed head contains the
  repaired executable hook
- **WHEN** official closeout performs its one atomic compare-and-swap
- **THEN** Git invokes that candidate hook directory only for the official
  transaction
- **AND** both protected refs are admitted or rejected together
- **AND** raw Git ref updates continue to use configured incumbent hook policy.

#### Scenario: Candidate hook is unavailable

- **GIVEN** the proposed candidate checkout lacks an executable
  reference-transaction hook
- **WHEN** official closeout is evaluated
- **THEN** ETHOS blocks before its CAS
- **AND** it does not run an unguarded transaction or silently select another
  hook directory.

#### Scenario: Rejected atomic update does not impersonate concurrency

- **GIVEN** atomic closeout update-ref returns an error and the accepted ref is
  still its captured old head
- **WHEN** ETHOS projects the closeout failure
- **THEN** it reports an atomic-update rejection with stderr
- **AND** it does not report accepted concurrent advancement.

#### Scenario: Independent release branch remains non-protected

- **GIVEN** the current policy declares an independent release branch
- **WHEN** that release ref changes outside an accepted_ff closeout
- **THEN** the hook does not require candidate-runner availability solely for
  that release ref
- **AND** existing non-protected admission behavior remains in force.

### Requirement: Cohort-bound full Work Lane convergence

ETHOS SHALL treat a request to converge multiple Work Lanes as an exact,
observation-bound local program and SHALL NOT interpret a branch prefix or
session instruction as reusable wildcard authority.

#### Scenario: a convergence cohort is frozen before mutation

- **GIVEN** a maintainer requests convergence of multiple existing Work Lanes
- **WHEN** the program begins
- **THEN** a separate owned governance Work Lane records the exact branch, HEAD,
  worktree binding, dirty state, lease/incarnation evidence, claim binding,
  intended disposition, and target-observation evidence for each lane
- **AND** later-created refs are outside the cohort unless separately admitted
- **AND** every effect recomputes mutable target facts before mutation.

#### Scenario: graph absorption does not erase a dirty overlay

- **GIVEN** a lane HEAD is equal to or an ancestor of accepted truth
- **AND** its linked worktree contains a dirty tracked or untracked delta
- **WHEN** convergence classifies the lane
- **THEN** the delta is preserved and semantically reviewed before retirement
- **AND** graph ancestry alone cannot authorize deletion.

#### Scenario: a valid foreign lease remains holder-bound

- **GIVEN** a cohort lane has a normalized valid lease owned by another holder
- **WHEN** convergence needs its implementation or closeout
- **THEN** normal holder completion or a quiesced exact handoff is preferred
- **AND** process absence, provider identity, or a supplied holder string does
  not grant takeover authority
- **AND** replay in an owned successor keeps the original lane observe-only.

#### Scenario: exceptional cohort resolution consumes accepted judgment

- **GIVEN** a cohort lane is dirty, missing trusted lease state, owner-uncertain,
  or requires irreversible retirement
- **WHEN** the lane is resolved
- **THEN** an accepted Chronicle has already bound the exact policy and target
- **AND** a fresh two-phase decision binds one exact observation and recovery
  plan
- **AND** dirty content is preserved before retirement
- **AND** a stale observation blocks the effect instead of falling back to raw
  Git deletion.

#### Scenario: local convergence completion keeps evidence planes separate

- **WHEN** all cohort intent has been integrated or explicitly superseded
- **THEN** strict carrier completion, parity, HEAD-bound executed proof,
  candidate landing, accepted-root closeout, and lane retirement are verified as
  distinct transitions
- **AND** recovery-package retention remains independent
- **AND** local completion does not claim remote push, hosted execution, or
  distribution publication.

### Requirement: Report distinguishes local publication and hosted observation state

ETHOS report SHALL expose local publication readiness and hosted provider
observation status as separate read-only projections without performing a
remote probe or minting proof, hosted-success, or publication authority.

#### Scenario: Current hosted observation is projected

- **WHEN** ethos report runs and the configured hosted observation artifact
  binds the current tracked head
- **THEN** report data SHALL include hosted_observation state, freshness,
  provider-state summary, and bounded observation gaps
- **AND** those gaps SHALL remain advisory rather than repository proof
  required_gaps
- **AND** hosted GitHub status claimed, hosted GitLab status claimed, and remote
  publication claimed SHALL remain false

#### Scenario: Hosted observation is missing invalid or stale

- **WHEN** the hosted observation artifact is missing, malformed, or bound to a
  different tracked head
- **THEN** report SHALL expose missing, invalid, or stale hosted observation
  state
- **AND** it SHALL provide a bounded next action to rerun the observation owner
  script
- **AND** the scorecard SHALL remain read-only

#### Scenario: Local publication readiness is projected

- **WHEN** ethos report summarizes current blockers and proof readiness
- **THEN** report data SHALL include a local_publication projection that
  distinguishes ready from blocked local state
- **AND** the projection SHALL list its local blockers
- **AND** remote publication claimed SHALL remain false
- **AND** the projection SHALL NOT replace the ethos publish transition verdict

### Requirement: Lifecycle claim semantic scope is behavior-exact

An active claim that attests universal adopter OpenSpec lifecycle SHALL declare `semantic_scope` promotion targets for the lifecycle command implementations and their behavioral regressions. It SHALL NOT use a broad CLI directory merely because the implementation resides there. The semantic-scope reader SHALL fail closed when any declared lifecycle implementation or regression target changes.

#### Scenario: Unrelated CLI reader change does not stale lifecycle evidence

- **WHEN** a change outside the declared lifecycle implementation and regression targets changes a CLI reader file
- **THEN** the lifecycle claim semantic digest remains current
- **AND** the claim reader does not emit `evidence.semantic_scope_stale`

#### Scenario: Lifecycle implementation change stales lifecycle evidence

- **WHEN** a declared lifecycle command implementation or behavioral regression target changes
- **THEN** the lifecycle claim reader emits `evidence.semantic_scope_stale`
- **AND** ETHOS requires a governed evidence refresh before the claim is clean

### Requirement: Refresh-base replay is signing-bound and compare-and-swap safe

When a Work Lane refresh requires SSH commit signing through a configured
file-backed key, ETHOS SHALL establish signing transport before the replay can
start. It SHALL revalidate the admitted Work Lane and candidate SHA snapshots,
replay the admitted Work Lane SHA against the admitted candidate SHA in
detached state, and compare-and-swap the Work Lane ref from its admitted old
SHA before attaching it again.

#### Scenario: unavailable signing transport blocks before replay

- **GIVEN** `commit.gpgsign` is truthy, `gpg.format` is `ssh`, and
  `user.signingkey` resolves to a file-backed key with no usable agent transport
- **WHEN** `lane refresh-base --apply` runs
- **THEN** it reports `refresh_signing_transport_unavailable`
- **AND** it does not start a rebase or advance the Work Lane ref.

#### Scenario: admitted snapshots move during preflight

- **GIVEN** a refresh has captured Work Lane and candidate SHA values
- **WHEN** either value changes before replay begins
- **THEN** it reports the corresponding `refresh_base_snapshot_stale` gap
- **AND** it does not start a rebase or advance the Work Lane ref.

#### Scenario: Work Lane moves before replay compare-and-swap

- **GIVEN** detached replay has produced a candidate-descended refreshed SHA
- **WHEN** the Work Lane ref no longer equals its admitted old SHA
- **THEN** ETHOS reports `refresh_base_snapshot_stale:work_lane`
- **AND** it reattaches to the newer branch state without overwriting that ref.

### Requirement: Committed Adopter Profile Policy At Closeout

ETHOS SHALL resolve adopter proof policy from the promoted committed tree when
accepted-root closeout evaluates an exact candidate advance before the accepted
worktree has reset to that candidate commit.  The implementation of this policy
SHALL remain subject to the active proof floor; a proof failure SHALL be
remediated in a separately active Change without weakening closeout policy,
source-budget limits, evidence binding, or the raw-reference-move guard.

#### Scenario: candidate proof policy is evaluated during accepted-root closeout

- **GIVEN** a candidate commit changes a valid non-product repository profile
  that defines its native proof gates
- **WHEN** a reference-transaction hook evaluates the proposed accepted-root
  advance before the accepted worktree resets to that candidate commit
- **THEN** ETHOS SHALL resolve the profile, required proof floor, gate
  descriptors, policy digest, and run conformance from the promoted committed
  tree
- **AND** a profile absent from that resolvable candidate tree SHALL be treated
  as absent rather than inherited from the accepted-old working tree
- **AND** raw accepted-root moves without a matching one-shot closeout intent
  SHALL remain blocked.

#### Scenario: closeout-policy remediation does not lower the acceptance bar

- **GIVEN** a Change introduces committed-profile closeout policy resolution
- **WHEN** it is prepared for candidate landing
- **THEN** it SHALL preserve candidate-tree policy resolution and the
  raw-reference-move guard
- **AND** it SHALL pass the existing proof floor without adding source-budget
  debt, allowance, or an exclusion for the remediation
- **AND** regenerated evidence and later proof SHALL bind the corrective HEAD.

### Requirement: Maintainer remote reconciliation preserves observed protected history

For a maintainer-authorized reconciliation of divergent protected repository
refs, ETHOS operations SHALL retain each fresh observed remote tip as an
ancestor of the proposed reconciliation head, use ordinary merge commits for
history integration, and keep local proof, remote ref mutation, and hosted
provider observation as distinct evidence classes.

#### Scenario: protected refs are divergent before reconciliation

- **WHEN** a maintained repository observes different protected `dev` or `main` tips across its configured forge providers
- **THEN** the reconciliation Lane records the exact observed tips before mutation
- **AND** it creates a claim-bound carrier that names the scope, fallback, and kill signal
- **AND** its proposed reconciliation head remains a descendant of every recorded tip

#### Scenario: local proof precedes protected remote update

- **WHEN** the reconciliation head has passed its required local proof and governed local closeout
- **THEN** each protected remote update is first tested with its own ordinary push dry-run
- **AND** no force update, rebase, reset-based ref movement, or stash-based conflict bypass is used
- **AND** later remote and hosted-provider observations are recorded without treating local proof as either result

### Requirement: Remote reconciliation continuation preserves historical carrier boundaries

If historical remote-reconciliation content landed but lifecycle work remains,
ETHOS SHALL preserve its archive without claiming completion and bind an active
continuation to the same episode Claim. If the original host worktree cannot
resume, the continuation SHALL use a distinct owned lane on current candidate,
retain only freshly observable context, and rerun current proof; historical
proof or reconstructed paths grant no current authority.

#### Scenario: remaining lifecycle work continues after historical archival

- **WHEN** a historical reconciliation archive records unfinished local closeout, remote observation, or retirement work
- **THEN** an active continuation records the transfer and binds the episode claim
- **AND** it preserves normal merge and no-force constraints
- **AND** it distinguishes local proof, remote mutation, remote observation, and hosted-provider observation

#### Scenario: Historical worktree is absent

- **GIVEN** a historical Change, claim, and evidence stream remain readable
- **AND** the original host worktree or its checkout-local temporary state is
  absent
- **WHEN** a successor begins continuity work
- **THEN** it records retained source identities, irrecoverable state, current
  Git and Work Lane anchors, and a no-reconstruction boundary
- **AND** it leaves the historical lane and its archive observe-only
- **AND** it binds the existing episode claim to the active successor carrier
  before a new proof, land, closeout, or publication attempt.

#### Scenario: Current proof follows retained historical meaning

- **GIVEN** a successor continuity packet has preserved the historical meaning
- **WHEN** the successor reaches a stable committed HEAD
- **THEN** ETHOS evaluates current source and regressions through current
  OpenSpec lifecycle and HEAD-bound proof
- **AND** it distinguishes that proof from historical proof, temporary runtime
  state, hosted CI, and remote publication.

### Requirement: Authorized Work Lane cohort closeout is exact and evidence-bound

Authorized cohort closeout SHALL evaluate each observed lane, never grant
wildcard foreign-lane authority. Before handoff, preservation, replay,
supersession, or retirement, its carrier SHALL bind branch/head, accepted
relation, lease/incarnation, Claim, dirty provenance, disposition, recovery, and
evidence. Replay also binds implementation, focused regression, owned proof,
and accepted absorption. Any target drift invalidates the decision.

#### Scenario: A visible foreign lane is not wildcard authority

- **WHEN** an owned carrier audits a visible foreign Work Lane
- **THEN** it records an exact target observation and allows only the native
  holder-bound or accepted exceptional lifecycle path for that target
- **AND** it does not allow a batch, wildcard, or stale observation to write,
  land, retire, or delete a different foreign Work Lane.

#### Scenario: A moving target invalidates its decision

- **WHEN** a target's head, dirty state, holder, lease generation, or relation
  to accepted truth changes after a decision was prepared
- **THEN** ETHOS blocks the planned apply effect for that decision
- **AND** the owned carrier re-observes the target before producing a new
  decision.

#### Scenario: Historical source is absorbed without historical topology

- **WHEN** a recovered Work Lane exposes behavior absent from the current
  contract
- **THEN** an owned current-baseline lane adds the smallest focused regression
  and implementation for that behavior
- **AND** its executed proof and accepted closeout identify the source lane as
  absorbed behavior, not as a merged historical branch
- **AND** only a later fresh native retirement transition may remove the source
  lane.

#### Scenario: Current-equivalent or deferred intent is not silently erased

- **WHEN** a source lane's behavior is already covered by accepted source and
  proof, or its proposal is outside the current product decision
- **THEN** the absorption record names the current proof or deferred decision
- **AND** it keeps the source lane intact until an exact retirement or later
  product/adopter admission path is separately established.

#### Scenario: Zero missing behavior selects preservation closeout, not integration

- **WHEN** an exact semantic matrix classifies every patch-inequivalent source
  change as accepted, superseded, obsolete, or intentionally deferred
- **AND** no product behavior remains missing from accepted truth
- **THEN** ETHOS prohibits merge, rebase, cherry-pick, refresh, and land of the
  historical Work Lane
- **AND** if the native decision/apply contract cannot bind and revalidate the
  accepted HEAD/relation, lease ID/epoch, exact target observation, completion
  state, and recovery package integrity, ETHOS treats the exceptional effect as
  unavailable
- **AND** the historical lane remains intact until a separately accepted product
  change implements those guards and reconciles any contradictory completion
  record
- **AND** only after that repair may ETHOS record the then-current accepted HEAD,
  recompute the target relation, reconfirm the matrix and zero-residual result,
  and prepare a fresh decision selecting
  `lane_resolution/preserve-retire` with verified recovery material,
  break-glass, and explicit irreversible confirmation
- **AND** any later accepted, target, lease, or completion-state drift blocks
  apply until a new observation and decision exist.

### Requirement: Dirty and unbound Work Lane content is preserved before destructive closeout

ETHOS SHALL preserve a dirty foreign Work Lane or diverged unbound Work Lane
reference before an irreversible closeout action.  The preservation outcome
SHALL record Git status provenance, exact target head, recoverable content
manifest or patch digest, semantic comparison result, and the resulting
disposition.  A clean accepted-absorption finding alone SHALL NOT discard an
unpreserved dirty overlay.

#### Scenario: Dirty foreign lane requires preservation first

- **WHEN** a full lane observation reports a foreign Work Lane with tracked,
  deleted, conflicted, or untracked content
- **THEN** the closeout carrier creates or retains a verifiable preservation
  package before requesting retirement
- **AND** the lane remains preserve-replay or blocked until its unique semantic
  delta is accepted or intentionally superseded.

#### Scenario: Diverged unbound ref remains recoverable

- **WHEN** an unbound Work Lane ref diverges from accepted truth
- **THEN** ETHOS requires a recoverable semantic or preservation outcome before
  its native unbound retirement path
- **AND** it does not delete the ref merely because it lacks a linked worktree.

### Requirement: Shadow parity external execution honors checkout runtime topology

ETHOS SHALL select the checkout-bound `build/runtime/venv/bin/python` for a
shadow-parity external command when that interpreter exists. It SHALL select
that runtime before a legacy root `.venv/bin/python`, so ignored migration
residue that cannot import ETHOS does not make a current Work Lane appear to
have an external command failure.

#### Scenario: Stale root environment does not block current parity

- **WHEN** a Work Lane has both `build/runtime/venv/bin/python` and a root
  `.venv/bin/python` that lacks the ETHOS package
- **THEN** shadow parity invokes the checkout-bound runtime for its external
  command
- **AND** it can produce current parity evidence instead of reporting an
  `external_command_failed` gap solely because of the stale root environment.

### Requirement: Final dual-remote submit absorption is proof-bound and non-destructive

When configured GitLab and GitHub submit refs carry a final divergent patch,
ETHOS SHALL retain each exact observed submit tip through ordinary merge
ancestry, execute local proof and governed local closeout before a protected
update, and delete a submit ref only after its tip is an ancestor of accepted
truth and its own normal deletion dry-run is accepted.

#### Scenario: Inputs move after a historical carrier archive

- **WHEN** a historical carrier has been archived but the candidate or a
  configured submit ref advances before its unresolved lifecycle stages run
- **THEN** ETHOS SHALL preserve that archive as historical evidence
- **AND** bind an active continuation to the same episode claim before a new
  merge, proof, closeout, remote update, or submit deletion is attempted
- **AND** the continuation SHALL re-observe the current inputs and retain its
  newly observed submit tip through ordinary merge ancestry.

#### Scenario: Divergent submit patch is reconciled

- **WHEN** a configured remote submit ref is not an ancestor of the current
  candidate head
- **THEN** an owner-bound, claim-bound Work Lane records its exact tip and
  integrates it with an ordinary merge
- **AND** the resulting proposed head retains both the candidate and submit
  histories as ancestors
- **AND** no force update, rebase, reset-based ref movement, or stash bypass is
  used.

#### Scenario: Publication follows local closeout

- **WHEN** the merged head has passed executed local proof and governed
  candidate/accepted closeout
- **THEN** each protected remote ref is tested by its own ordinary push dry-run
  before update
- **AND** remote ref observation and hosted-provider observation remain distinct
  from the local proof result
- **AND** a submit ref is deleted only after accepted ancestry and its own
  deletion dry-run are verified.

### Requirement: Campaign-terminal protected publication admission

For `publication.mode = "campaign_terminal"`, ETHOS SHALL separate structural
publication validity from terminal-progress advisories. Malformed or unbound
contracts block protected push. Active state, unfinished steps, budget or debt
gaps, and compression progress remain explicit advisories and do not block an
ordinary non-force protected update after executed proof and candidate/accepted
closeout. Receiving-branch protection remains authoritative.

#### Scenario: Non-terminal compression campaign blocks protected push

- **GIVEN** an active `campaign_terminal` campaign has planned, active, or
  non-retired steps, unmet terminal source budget, or active temporary debt
- **AND** the pushed `dev` or `main` head has executed local proof and governed
  candidate/accepted closeout
- **WHEN** pre-push admission evaluates a configured protected destination
- **THEN** campaign progress SHALL appear in `campaign_publication.advisory_gaps`
- **AND** it SHALL add no campaign-progress item to pre-push `required_gaps`
- **AND** pushes to `work/*` remain governed by ordinary remote branch policy.

#### Scenario: Terminal campaign admits ordinary protected-push checks

- **GIVEN** every active `campaign_terminal` campaign is closed, every step is
  archive-complete and retired, terminal source-budget targets are met, and no
  temporary debt record remains active
- **WHEN** pre-push admission evaluates a protected destination
- **THEN** the campaign publication report SHALL add no required or advisory gap
- **AND** identity, executed-proof, candidate-topology, reconciliation, and
  provider-specific checks SHALL remain independently enforced.

#### Scenario: Per-Change temporary debt does not block local progression

- **GIVEN** a `campaign_terminal` campaign is active and source-budget
  enforcement is `campaign_terminal` with declared unexpired temporary debt
- **WHEN** a bounded Change completes its local proof and closeout lifecycle
- **THEN** campaign reporting SHALL expose the debt as terminal-progress advice
- **AND** it SHALL not classify the Change or an ordinary protected push as
  blocked solely because the campaign terminal target is not yet met.

#### Scenario: Campaign terminal budget keeps debt lifecycle local

- **GIVEN** source-budget enforcement is `campaign_terminal`
- **WHEN** a local Change increases effective source while declared debt remains
  within its maximum and active lifecycle
- **THEN** source-budget validation SHALL not block that local Change solely for
  current-size or terminal-target non-attainment
- **AND** invalid policy, debt-cap overflow, expired debt, and stale debt SHALL
  remain local blocking gaps
- **AND** full proof and terminal compression closeout SHALL still require
  terminal targets and no active debt.

#### Scenario: Invalid Campaign declaration fails closed

- **GIVEN** a Campaign TOML file exists but violates
  `system/schemas/kernel/campaign.schema.json`
- **WHEN** Campaign status or protected-publication admission reads the manifest
- **THEN** the reader SHALL expose a `campaign_manifest_schema_invalid` gap
- **AND** protected publication SHALL be blocked instead of treating the
  Campaign as unconfigured.

#### Scenario: Campaign action commands remain external

- **WHEN** Campaign publication projection selects local continuation or
  protected publication
- **THEN** the domain projection SHALL return a stable action identifier
- **AND** CLI command text SHALL be resolved through `system/commands.toml`
- **AND** Python SHALL NOT encode a Campaign name, provider topology, or parallel
  action vocabulary.

#### Scenario: Filtered Campaign status preserves repository scope

- **WHEN** `ethos campaign status --campaign <id> --json` selects one Campaign
- **THEN** `data.campaigns` SHALL contain the selected Campaign view
- **AND** `data.publication.scope` SHALL remain `repository`
- **AND** filtering SHALL NOT omit another Campaign or source-budget binding from
  structural publication admission or terminal-progress advice.

#### Scenario: Hook evaluates the named remote

- **WHEN** the Git pre-push hook receives `github` as its remote name
- **THEN** both its base and enriched push-admission evaluations SHALL receive
  `remote_name = "github"`
- **AND** emitted remote diagnostics and branch admission SHALL describe GitHub,
  not the default `origin`.

### Requirement: Detached temporary worktree housekeeping is fail-closed

ETHOS SHALL inventory detached Git worktrees without treating detachment as
cleanup authority. It SHALL remove a worktree only after explicit authorization
when the entry is detached, clean, unlocked, below a controlled temporary root,
not the audited checkout, and unchanged at immediate reobservation.

#### Scenario: Clean detached temporary worktree is removable

- **WHEN** `ethos lane housekeeping --json` observes a clean detached worktree
  below a controlled temporary root
- **THEN** it reports that exact path as removable without changing Git state
- **AND** removal occurs only with `--authorize --apply`.

#### Scenario: Valuable or active worktree remains protected

- **WHEN** a worktree is dirty, unreadable, branch-bound, Git-locked, outside
  controlled temporary roots, or is the audited checkout
- **THEN** housekeeping reports a machine-readable protection reason
- **AND** it does not remove the worktree even in authorized apply mode.

#### Scenario: Candidate changes before removal

- **WHEN** a planned removable worktree changes before the effect
- **THEN** ETHOS reports a stale-candidate gap
- **AND** it preserves the changed worktree.

#### Scenario: Git inventory is unavailable

- **WHEN** Git cannot return the registered worktree inventory
- **THEN** housekeeping reports a blocking inventory gap
- **AND** it does not project an empty removable set as successful inspection.

### Requirement: Archived Work Lane candidate-drift continuation

ETHOS SHALL continue useful work from an archived or historically proved Work
Lane through an owned, claim-bound successor based on the latest candidate. It
MUST preserve predecessor ancestry, keep historical carriers immutable, and
regenerate every projection and proof whose validity depends on the new HEAD.

#### Scenario: Semantic refresh conflict fails closed

- **WHEN** the official candidate-base refresh encounters a semantic conflict
- **THEN** ETHOS MUST abort the replay and report `refresh_base_failed`
- **AND** it MUST restore the Work Lane branch and worktree to the expected clean
  head
- **AND** no manual rebase continue, skip, raw ref movement, or history
  replacement may be used to bypass the failure.

#### Scenario: Latest candidate starts a successor

- **WHEN** useful predecessor work cannot land because its candidate base is
  stale and semantic refresh failed closed
- **THEN** an owned successor MUST start from the latest observed candidate
- **AND** it MUST bind the same episode claim
- **AND** the predecessor Lane, archived Change, historical Chronicle, and proof
  receipt MUST remain observe-only.

#### Scenario: Successor preserves ancestry and regenerates evidence

- **WHEN** the successor absorbs the useful predecessor head
- **THEN** it MUST use a no-fast-forward merge with the candidate base as first
  parent and the predecessor head as second parent
- **AND** candidate-authoritative parity, configuration, and gate projections
  MUST be retained but treated as stale after the merge
- **AND** parity MUST be regenerated and proof MUST execute against the resulting
  current HEAD rather than reuse a historical receipt.

#### Scenario: Candidate advances after a topology-bearing merge

- **WHEN** candidate advances again after the continuation has created a
  topology-bearing merge but before land
- **THEN** a further owned successor MUST start from the newer candidate and
  no-fast-forward absorb the completed continuation head
- **AND** ETHOS MUST NOT linearize or discard the existing merge topology merely
  to refresh the base.

#### Scenario: Historical facts are corrected without archive mutation

- **WHEN** independent replay or review corrects a fact recorded by the
  historical carrier
- **THEN** the active continuation MUST record a superseding correction with its
  reproducible inputs and digest
- **AND** the archived Change, historical Chronicle, and historical proof
  receipt MUST NOT be rewritten.

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

`ethos lane retire unbound` SHALL admit one head-matched, accepted-ancestor
unbound `work/*` ref with no worktree and an active Claim bound to an accepted
Chronicle. Lease is absent or one exact
invocation-bound holder/ID/epoch/head generation. Chronicle SHALL bind operation,
target branch/head, and Claim; Claim bytes match accepted. One carrier authorizes
one target. Apply requires authorization, break-glass, and irreversible
confirmation; provider, session, or host grants no authority.

#### Scenario: Exact accepted-ancestor residue is inspected

- **WHEN** an operator supplies an unbound `work/*` ref that is an accepted
  ancestor, has no linked worktree and no active lease, and supplies a matching
  accepted Chronicle and Claim, expected head, and reason
- **THEN** dry-run reports `ready_to_retire_unbound_exceptional`
- **AND** it reports the exact observation without deleting the ref
- **AND** it reports that its output does not mint reusable authority.

#### Scenario: One carrier does not authorize another target

- **WHEN** an operator supplies a Chronicle or Claim for a different unbound ref
- **THEN** the command SHALL block the mismatched target before mutation
- **AND** the target SHALL require its own expected head, Claim, Chronicle,
  current observation, and receipt.

#### Scenario: A non-exact or non-accepted target is refused

- **WHEN** the target is linked, has a foreign, ambiguous, stale, or
  head-mismatched lease, is not an accepted ancestor, lacks a
  Chronicle-bound active Claim, has a mismatched expected head, or its Chronicle
  or Claim is missing, unaccepted, generic, stale, or names another target
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL leave the target ref and any lease intact.

#### Scenario: Exceptional controls are incomplete

- **WHEN** apply omits authorization, break-glass, or irreversible confirmation
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL report the missing machine-readable control gaps.

#### Scenario: Unavailable source holder is recovered only by exact accepted policy

- **WHEN** a target-specific accepted Chronicle records
  `lease_recovery: owner_unavailable`, the exact active source lease ID, holder,
  epoch, expected head, and a SHA-256 digest of the recorded absolute source
  worktree path, and that path is absent
- **AND** an explicitly confirmed invocation uses
  `--owner-unavailable-recovery` from a different non-empty actor identity
- **THEN** ETHOS MAY revoke only that exact source lease generation through the
  native lease CAS before the existing compare-and-delete transition
- **AND** a present source path, an invalid or mismatched Chronicle lease tuple,
  a missing recovery actor, or a same-holder invocation SHALL block without
  deleting the ref or lease
- **AND** this exception SHALL remain exact-target, receipt-bound, and
  vendor-neutral; process absence, a provider/session label, or a supplied
  holder string alone SHALL NOT authorize takeover.

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

Before exceptional unbound effect, ETHOS SHALL reobserve the exact target,
accepted policy, lease, and protected refs. It SHALL create a no-clobber attempt,
compare-delete only `refs/heads/<branch>` at expected head, then require target
ref and reader absence plus unchanged protected refs before a no-clobber receipt.
It SHALL NOT remove worktrees, mutate remotes, or use unconstrained deletion.

#### Scenario: Current holder relinquishes one exact lease generation

- **WHEN** all ordinary exceptional controls have passed and the target has an
  active lease whose holder equals the current `ETHOS_ACTOR`, whose ID and epoch
  are present, and whose expected head equals the target head
- **THEN** ETHOS MAY revoke only that exact generation through the native lease
  CAS after publishing its attempt record
- **AND** the attempt and successful receipt bind the exact lease generation and
  CAS result
- **AND** ETHOS SHALL reobserve all non-lease retirement bindings and require
  no active lease before the compare-and-delete ref effect.

#### Scenario: Lease relinquishment remains fail-closed

- **WHEN** a target lease is absent, foreign, malformed, stale, head-mismatched,
  replaced, or cannot be revoked by the exact CAS
- **THEN** ETHOS SHALL leave the source ref intact and report the observed gap
- **AND** it SHALL not claim retirement or use raw lease or ref deletion.

#### Scenario: Apply deletes only the observed ref

- **WHEN** all exceptional conditions remain stable through the pre-effect
  reobservation and the compare-and-delete succeeds
- **THEN** ETHOS SHALL report `retired_unbound_exceptional`
- **AND** its receipt SHALL bind the before and after observations, accepted
  Chronicle digest, effect, and postconditions
- **AND** the target ref, unbound reader entry, and active lease SHALL be absent
  while protected refs remain unchanged.

#### Scenario: Observation or postcondition drifts

- **WHEN** the target, accepted Chronicle, protected refs, lease state, record
  publication, or post-effect observation differs from the admitted facts
- **THEN** ETHOS SHALL report a blocked local residue with exact gaps
- **AND** it SHALL not delete a newer ref, remove an active lease, or claim the
  retirement completed.

#### Scenario: Target-specific evidence remains vendor-neutral

- **WHEN** a target-specific accepted Claim and Chronicle authorize a later
  exceptional unbound Work Lane retirement
- **THEN** their authority SHALL remain limited to their exact branch and head
- **AND** ETHOS SHALL NOT infer deletion authority from an agent vendor,
  account, session, host path, or another target's evidence carrier.

### Requirement: Ref-absent owner-unavailable partial effects are reconciled only through exact native lease CAS

`ethos lane retire reconcile-ref-absent` SHALL reconcile only an immutable prior
attempt whose ref and path are absent while its exact foreign lease remains. It
requires accepted-byte-identical Claim and Chronicle, exact source lease tuple,
a distinct recovery actor, and Chronicle binding to prior operation ID,
accepted head, Claim, Chronicle ref, and digests. Apply requires authorization,
break-glass, and irreversible confirmation; it neither recreates nor deletes the
source ref.

#### Scenario: Exact ref-absent residue is reconciled

- **WHEN** the ref and source worktree are absent, protected refs and current
  accepted policy remain stable, and the current lease exactly matches the
  accepted Chronicle and immutable source attempt
- **THEN** ETHOS SHALL revoke only that exact source lease generation through a
  native CAS
- **AND** it SHALL report `reconciled_ref_absent_owner_unavailable_lease` only
  after postconditions prove ref, worktree, and lease absence plus unchanged
  protected refs and Chronicle binding.

#### Scenario: Reconciliation observation or evidence drifts

- **WHEN** a source ref or worktree reappears, or the lease tuple, source path,
  current Chronicle/Claim bytes, source attempt, accepted control root, or
  protected refs drifts
- **THEN** ETHOS SHALL block before lease mutation
- **AND** it SHALL preserve the foreign lease and all refs unchanged.

### Requirement: Versioned local-state schema evolution

ETHOS SHALL support only the current subject-keyed lease schema: generation
state in `payload_json`, binary unique subject identity, and ownership limited
to `leases`. It SHALL reject retired shapes without migration or a lease-owned
database version ledger while preserving unrelated tables. The database path
SHALL derive from Git common-directory identity; destructive linked retirement
still requires the accepted checkout.

#### Scenario: A fresh state database is initialized

- **WHEN** no state schema exists
- **THEN** ETHOS creates the current subject-keyed lease schema
- **AND** SQLite enforces subject uniqueness
- **AND** it does not create a database-wide migration ledger.

#### Scenario: A version-1 state database is opened

- **WHEN** ETHOS opens a database whose `leases` table has a retired shape or a
  noncanonical subject constraint
- **THEN** ETHOS fails closed without translating or rewriting the database
- **AND** current local coordination must be recreated through the canonical
  lifecycle.

#### Scenario: Another owner shares the state database

- **WHEN** the current lease table coexists with tables owned by another
  local-state capability
- **THEN** lease initialization validates only its exact owned schema subset
- **AND** it preserves every unrelated table and row unchanged.

#### Scenario: A current database is initialized again

- **WHEN** the exact current subject-keyed lease schema already exists
- **THEN** initialization is idempotent
- **AND** no active coordination row is rewritten or deleted.

#### Scenario: The accepted branch is not checked out

- **WHEN** another protected branch occupies the canonical repository path
- **THEN** a linked Work Lane reads the same Lease generation and Claim binding
- **AND** destructive retirement still requires its accepted-checkout control root.

### Requirement: Explicit conservative local-state maintenance

ETHOS SHALL keep local-state audit read-only by default and SHALL require an
explicit maintenance action before pruning disposable state.

#### Scenario: Audit runs without maintenance authorization

- **WHEN** the local-state owner runs in its default audit mode
- **THEN** it reports migration residue, lease candidates, proof candidates, and
  ignored-state inventory
- **AND** it does not mutate SQLite, proofs, refs, worktrees, or snapshots.

#### Scenario: Expired orphan leases are maintained

- **WHEN** explicit maintenance evaluates an expired lease whose branch ref,
  linked worktree, and recorded path are all absent
- **THEN** ETHOS deletes that exact lease row and reports its identity
- **AND** it retains every unexpired, current, ambiguous, or still-observable
  lease.

### Requirement: Ref-bound proof retention

ETHOS SHALL treat HEAD-keyed local proof as disposable readiness state while
preserving the current HEAD record and every proof whose commit remains reachable
from a current Git ref.

#### Scenario: A proof HEAD is unreachable from all refs

- **WHEN** explicit maintenance finds a well-formed proof record whose named Git
  HEAD is not reachable from any current ref and is not current HEAD
- **THEN** it removes that proof record and reports its path and HEAD
- **AND** current or ref-reachable proof records remain unchanged.

### Requirement: Recovery material is preservation-bound before cleanup

ETHOS SHALL NOT delete a recovery snapshot set until a complete operator archive
and a digest-bound Chronicle receipt have been verified.

#### Scenario: Recovery snapshots contain unique Git and dirty-worktree material

- **WHEN** an operator closes a recovery snapshot set
- **THEN** the archive manifest binds every entry, archive digest, byte size,
  bundle verification result, archive location, and repository HEAD
- **AND** extraction and bundle verification succeed before the source snapshot
  directory is removed.

### Requirement: Accepted-root closeout is bound to one audited candidate HEAD

ETHOS SHALL bind candidate audit, control-replacement admission, executed proof,
and accepted-root mutation to one observed candidate HEAD.

#### Scenario: Candidate HEAD changes during or after closeout audit

- **WHEN** accepted-root closeout observes the candidate HEAD before audit
- **THEN** the audit receives that HEAD as its claim binding
- **AND** closeout re-observes the candidate after audit and immediately before
  mutation
- **AND** any mismatch blocks control admission and accepted-root movement.

### Requirement: Tracked lifecycle does not imply local-state maintenance effects

ETHOS SHALL require an explicit, authorized, digest-bound maintenance apply and
its own receipt before reporting that ignored local state changed. Tracked
OpenSpec, Git, land, closeout, or publish transitions SHALL NOT mint such an
effect.

#### Scenario: A tracked Change archives and lands without maintenance apply

- **WHEN** an OpenSpec carrier validates, archives, lands to candidate, or closes
  out accepted root without an explicit local-state maintenance apply
- **THEN** ETHOS does not infer that a live SQLite database migrated
- **AND** it does not infer lease or proof pruning, operator archive creation, or
  recovery-source deletion.

#### Scenario: A maintenance effect is claimed

- **WHEN** evidence states that local leases, proofs, databases, or recovery
  material changed
- **THEN** the evidence names the authorized apply command, exact inventory
  digest, affected local root, result receipt, and postcondition verification
- **AND** fixture, copied-state, dry-run, OpenSpec, land, closeout, and publish
  receipts are insufficient substitutes.

### Requirement: Bounded Coordination Aggregate Detail State

ETHOS SHALL derive coordination aggregate detail state from the reader mode
selected by the caller, not from the number or contents of visible foreign Work
Lane rows.

#### Scenario: Empty bounded inventory remains deferred

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs with foreign path-scope expansion disabled
- **THEN** coordination `detail_state` SHALL be `deferred`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL be `null`
- **AND** observable foreign-lane and lease counts SHALL remain available.

#### Scenario: Empty full inventory remains exact

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs in its full default mode
- **THEN** coordination `detail_state` SHALL be `exact`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL all be zero.

### Requirement: Real history-residue effects use a distinct local closeout successor

The system SHALL keep the dated tracked-work archive immutable and SHALL bind any
later real local-state maintenance to a distinct successor claim and exact
external receipt.

#### Scenario: Historical operator apply is admitted without rewriting the predecessor

- **WHEN** a verified maintenance receipt postdates an archive that excluded real effects
- **THEN** a new successor records the receipt HEAD, inventory digest, artifact digests, deletion counts, and source postconditions
- **AND** the predecessor archive remains byte-for-byte unchanged
- **AND** the record does not infer current ignored-state counts from historical apply counts

#### Scenario: Local closeout preserves authority boundaries

- **WHEN** the successor completes its archive and promotion transitions
- **THEN** accepted closeout uses `maintainer_break_glass_local`
- **AND** remote publication and hosted execution remain deferred and unclaimed
- **AND** r7 plus foreign and unbound lanes remain observe-only
- **AND** only the current owned lane is eligible for retirement

#### Scenario: Control replacement requires external verification

- **WHEN** the final candidate differs on configured control paths
- **THEN** accepted closeout requires an external control-replacement receipt outside the candidate tree
- **AND** the receipt binds exact accepted and candidate heads, control paths, both control digests, verifier digest, and executed-proof digest

### Requirement: Adopter profile is a strict, migratable repository binding
ETHOS SHALL validate adopter profiles through one typed current binding. It may
accept only explicitly enumerated historical fields needed for deterministic
normalization. Normalization discards only retired metadata and translates former
`roots.rules = "."` only with its complete historical envelope; unknown,
malformed, or incompatible data SHALL fail.

#### Scenario: Former profile normalizes to the current contract
- **WHEN** an adopter profile contains the historical version metadata and
  repository metadata with their declared historical values, including the
  former `roots.rules = "."` workaround for one root-level normative file
- **THEN** ETHOS SHALL load the profile as valid current contract data
- **AND** it SHALL preserve current typed roots, proof gates, and OpenSpec
  material paths
- **AND THEN** it SHALL derive `normative_sources = ["guidelines.md"]` only
  when that former declaration did not already declare normative sources.

#### Scenario: Unsupported legacy data remains blocked
- **WHEN** an adopter profile contains an unknown field, an invalid path, a
  malformed retired field, or a current-profile use of `roots.rules = "."`
- **THEN** ETHOS SHALL report
  `adopter_profile_invalid:.ethos/profile.toml`
- **AND** it SHALL not silently ignore or reinterpret the data.

### Requirement: Normative files remain distinct from directory roots
ETHOS SHALL allow an adopter profile to declare one or more repository-relative
normative source files independently from its directory roots. It SHALL retain
the existing path safety rules for roots and SHALL not treat a declared file as
a directory.

#### Scenario: Root-level normative source is declared
- **WHEN** an adopter declares `normative_sources = ["guidelines.md"]`
- **THEN** ETHOS SHALL include `guidelines.md` in profile evidence-root
  candidates
- **AND** it SHALL keep `roots.rules` as an ordinary safe repository path.

### Requirement: Invalid adopter profile commands return structured blocks
Every public ETHOS reader, planning, proof, landing, report, and OpenSpec
lifecycle command SHALL return a structured `EthosResult` when the target
adopter profile is invalid. The result SHALL contain the stable invalid-profile
gap and SHALL not emit an uncaught traceback as its command result.

#### Scenario: JSON reader observes an invalid profile
- **WHEN** `ethos orient --json` or `ethos report --json` targets an invalid
  adopter profile
- **THEN** it SHALL emit parseable JSON with `ok = false`
- **AND** `required_gaps` SHALL contain
  `adopter_profile_invalid:.ethos/profile.toml`.

#### Scenario: Enforcing proof command observes an invalid profile
- **WHEN** `ethos prove --json` targets an invalid adopter profile
- **THEN** it SHALL emit parseable blocked JSON and exit non-zero
- **AND** it SHALL not start a mutation or create proof evidence.

#### Scenario: Landing does not mask an invalid adopter profile
- **WHEN** `ethos land --json` targets an invalid adopter profile
- **THEN** it SHALL emit parseable JSON with the invalid-profile gap before
  reporting another mutation-admission gap
- **AND** `ethos land --apply --json` SHALL exit non-zero after emitting that
  same structured result.

### Requirement: Minimal Adoption Binding

ETHOS SHALL bootstrap a governed repository with only the strict tracked
binding carrier required by current runtime semantics. Optional documentation,
decision, OpenSpec capability, skill, evidence, release, schema,
generated-artifact, or hosted-provider surfaces SHALL be created only by the
capability that owns them.

#### Scenario: A repository is adopted

- **WHEN** `ethos adopt --apply --authorize --expect-head <HEAD>` runs on an
  eligible Git repository
- **THEN** the planned and written file set SHALL contain only
  `.ethos/profile.toml`
- **AND** the profile SHALL bind a non-empty adopter identity and non-empty
  OpenSpec material paths through the strict frozen repository-profile contract
- **AND** the repository SHALL be recognized as an adopter
- **AND** no `.gitkeep`, provider CI, skill package, generic documentation,
  decision topology, capability family, compatibility state, or optional
  governance carrier SHALL be created.

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles the default adoption binding
- **THEN** the same strict frozen Pydantic declaration SHALL validate both the
  in-memory binding and its serialized TOML
- **AND** native TOML serialization SHALL produce the tracked binding
- **AND** no adoption-scaffold packaged template, renderer manifest, profile
  registry, family registry, skill registry, digest snapshot, or Jinja render
  environment SHALL be required.

#### Scenario: Parse-only Jinja measurement does not restore adoption rendering

- **WHEN** the product package includes Jinja2 for Budget Contract v2 source
  measurement
- **THEN** adoption SHALL still plan only `.ethos/profile.toml`
- **AND** no Jinja template resource, render environment, or adoption scaffold
  authority SHALL be restored.

#### Scenario: Existing bootstrap content differs

- **WHEN** adoption encounters a differing nonempty, symlinked, non-regular, or
  unreadable `.ethos/profile.toml`
- **THEN** apply SHALL fail with `adoption_conflict:.ethos/profile.toml`
- **AND** no compatibility merge, migration, update, alias, overlay, or parallel
  full scaffold SHALL be offered
- **AND** an empty binding MAY be replaced atomically and identical content MAY
  be retained.

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has no matching material change and has not selected
  an optional capability
- **THEN** absent docs, claims, skills, schemas, generated artifacts, hosted
  providers, or OpenSpec workspace carriers SHALL NOT become bootstrap gaps
- **AND** native correctness and material-scope requirements SHALL remain
  independently fail closed.

### Requirement: Current product revision one-binding external-adopter observation is bounded and durable

ETHOS SHALL preserve a provider-neutral observation of the current product
revision against isolated adopter clones using the one binding contract.

#### Scenario: Missing binding is created without unrelated writes

- **WHEN** adoption addresses an isolated clean Git clone without
  `.ethos/profile.toml`
- **THEN** dry-run SHALL plan exactly that one binding carrier
- **AND** authorized exact-HEAD apply SHALL write only that carrier
- **AND** unrelated adopter-owned files and the source seed checkout SHALL remain
  unchanged.

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** adoption encounters a differing nonempty `.ethos/profile.toml`
- **THEN** the observation SHALL record `adoption_conflict:.ethos/profile.toml`
- **AND** unrelated adopter-owned surfaces SHALL remain outside the write plan
- **AND** the source adopter checkout SHALL remain unchanged.

#### Scenario: Current observation is promoted without private coupling

- **WHEN** the raw bundle is promoted into product evidence
- **THEN** the tracked record SHALL omit workstation paths, adopter-private
  identity, credentials, accounts, keys, and provider-local configuration
- **AND** it SHALL bind the product and adopter revisions, one-binding create and
  conflict outcomes, raw-bundle digest, and whether a push occurred
- **AND** it SHALL NOT claim native-backend parity, semantic correctness, hosted
  execution, authority, or independent review unless a separate verifier
  actually establishes that claim.

### Requirement: Lease generation transitions compile from one declaration

ETHOS SHALL define renew, resume, handoff-offer, and handoff-accept operation
IDs, guard requirements, planned and applied states, and effect fields in the
tracked workflow declaration. The CLI SHALL supply current facts to one pure
reducer and SHALL dispatch only the effect named by the resulting
declaration-owned plan.

#### Scenario: A declared lease generation transition is evaluated

- **WHEN** renew, resume, handoff offer, or handoff accept is requested
- **THEN** ETHOS loads the matching declared lease transition
- **AND** the pure reducer returns its ordered gaps and state
- **AND** no parallel procedural operation matrix owns the same behavior.

### Requirement: Linked Work Lane retirement has one generation-bound effect

ETHOS SHALL route landed and superseded linked Work Lane retirement through one
strict request and semantic owner. Under a SQLite generation lock it SHALL bind
the actor, complete lease generation and payload identity, lane ref, and
expected head; then recheck the accepted control root and head, lane relation,
linked checkout head, and cleanliness. It SHALL remove only that clean checkout
and compare-and-delete only the exact lane ref in a Git transaction that also
verifies the accepted ref.

#### Scenario: Exact lease generation changed after planning

- **WHEN** the lease ID, holder, epoch, lane ref, expected head, row expiry, or
  raw payload digest no longer matches the planned linked retirement
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current lease intact.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS rolls back the lease deletion
- **AND** it restores the exact lane ref only if that ref remains absent
- **AND** it reports whether the no-clobber compensation succeeded.

#### Scenario: Landed and superseded commands share one owner

- **WHEN** a caller invokes ordinary landed or superseded linked retirement
- **THEN** both CLI commands construct the same strict request model and call
  the same linked-retirement effect
- **AND** no wrapper, re-export, compatibility summary, or parallel Python effect
  remains.

### Requirement: Lease generation identity is complete across boundaries

ETHOS SHALL represent one exact lease generation with its lease ID, holder,
epoch, lane ref, expected head, row expiry, and raw payload SHA-256 across
workspace status, handoff packages, accepted Chronicle bindings, retirement
attempts, receipts, and mutation effects. It SHALL reject incomplete or stale
bindings and SHALL NOT support a parallel legacy fingerprint.

#### Scenario: Handoff or Chronicle omits a mutable lease fact

- **WHEN** an otherwise matching lease binding omits or changes row expiry or
  raw payload SHA-256
- **THEN** ETHOS rejects the handoff or exceptional retirement
- **AND** the current lease and carrier remain unchanged.

#### Scenario: Unavailable-holder recovery is admitted

- **WHEN** accepted policy admits unavailable-holder retirement for one complete
  foreign lease generation
- **THEN** ETHOS calls the same exact revoke primitive used by ordinary holder
  relinquishment
- **AND** no unavailable-holder wrapper or parallel destructive effect exists.

#### Scenario: Cross-host destination import is acknowledged

- **WHEN** the package target actor imports one verified handoff package
- **THEN** ETHOS creates one destination-local Lease generation
- **AND** its content-addressed acknowledgement binds the package, target holder,
  lane/head, incarnation, Lease ID, epoch, expected head, expiry, and payload
  SHA-256
- **AND** edited, incomplete, or non-target acknowledgements cannot authorize
  source revocation.

#### Scenario: Cross-host import fails after Lease acquisition

- **WHEN** destination restoration fails after the new Lease is acquired
- **THEN** ETHOS removes only the exact created Git carriers
- **AND** revokes only that exact Lease generation after carrier absence is
  proven
- **AND** uncertain compensation retains observable state and fails closed.

#### Scenario: The same content-addressed package is exported again

- **WHEN** the derived package directory already exists
- **THEN** ETHOS verifies and reuses the identical immutable package
- **AND** it never recursively deletes or replaces existing package content.

### Requirement: Work Lane start is no-clobber and compensation-bound

ETHOS SHALL reject a Work Lane start before lease acquisition when the target
path or lane ref already exists. It SHALL recheck both after acquiring the new
lease. If Git worktree creation fails, ETHOS SHALL remove only a linked
worktree and ref proven to match the requested path, branch, and leased expected
head. It SHALL revoke the newly acquired lease only after both exact carriers
are proven absent.

#### Scenario: Target carrier already exists

- **WHEN** the requested target path or lane ref exists before lease acquisition
- **THEN** ETHOS blocks Work Lane start
- **AND** it creates no lease and does not modify the existing carrier.

#### Scenario: Carrier cleanup is incomplete

- **WHEN** failed Work Lane creation cannot remove the exact linked worktree or
  compare-and-delete the exact lane ref
- **THEN** ETHOS retains the lease
- **AND** it reports the failed cleanup boundary without claiming rollback.

#### Scenario: Failed creation leaves no carrier

- **WHEN** Git worktree creation fails and every carrier created by the attempt
  is proven absent
- **THEN** ETHOS revokes only the newly acquired exact lease generation
- **AND** unrelated leases, paths, and refs remain unchanged.

### Requirement: Resolution Decisions and Receipts are semantically disjoint

ETHOS SHALL keep authorization and realized outcome as separate facts. A lane
resolution Decision SHALL carry the admitted disposition. A completion Receipt
SHALL carry only its realized state and SHALL link to the Decision through
`decision_id`; it SHALL NOT repeat disposition. Handoff, Decision, and Receipt
contracts SHALL reject coercive scalar values and Git object IDs whose width is
not exactly 40 or 64 hexadecimal characters.

#### Scenario: A resolution effect completes

- **WHEN** an admitted resolution effect writes its completion Receipt
- **THEN** the Receipt records the exact realized state
- **AND** `decision_id` identifies the authorizing Decision
- **AND** no Receipt disposition, alias, compatibility field, or parallel
  outcome vocabulary is serialized.

#### Scenario: A wire payload relies on coercion or an ambiguous object ID

- **WHEN** a handoff or resolution payload supplies a boolean as an integer, a
  lease epoch as a string or boolean, or a Git object ID of intermediate width
- **THEN** both the typed contract and its JSON Schema boundary reject it
- **AND** no lifecycle effect begins.

### Requirement: Protected-ref semantics are candidate-commit bound

Protected-ref transitions SHALL execute the semantic runner from the candidate
HEAD's committed project, lockfile, package metadata, and initializers, using
locked, offline, isolated dependency resolution with `PYTHONPATH` cleared. They
SHALL reject ignored candidate runtimes, accepted-checkout interpreters, and
missing or mismatched committed inputs. The proof floor SHALL match the
committed repository role.

#### Scenario: Candidate runtime state attempts to override committed semantics

- **WHEN** a candidate ignored interpreter, inherited `PYTHONPATH`, accepted
  interpreter, uncommitted lockfile, or uncommitted package source differs from
  the candidate HEAD
- **THEN** the protected-ref transition does not execute that state
- **AND** missing or mismatched committed candidate inputs block the transition.

#### Scenario: A product-root control revision carries adopter proof

- **WHEN** the committed candidate tree is a product root but its proof was
  generated while an adopter profile still classified the worktree
- **THEN** admission requires the product proof floor and reports every missing
  product gate
- **AND** it does not reinterpret the proof through a `full` option or weaken
  the promotion floor.

### Requirement: Archived evidence does not own runtime replay

ETHOS SHALL NOT hard-code one archived Claim ID, dated archive carrier, or fixed
historical file set into Work Lane rebase execution. It SHALL resolve generated
parity conflicts through the parity projection path and declarative source-budget
ledger conflicts through the generic semantic ledger path.

#### Scenario: Historical one-off conflict shape reappears

- **WHEN** a rebase conflict matches a retired Claim-specific file set
- **THEN** ETHOS does not auto-resolve it from the historical Claim or archive
- **AND** the generic current conflict rules either resolve it or fail closed.

### Requirement: Post-lease ownerless remainders receive lane-specific semantic absorption

ETHOS SHALL resolve post-lease ownerless remainder lanes through exact
lane-specific semantic judgment before any native retirement effect.

#### Scenario: clean post-lease lanes are absorbed rather than blanket-preserved

- **GIVEN** a clean linked Work Lane has no current lease or Claim and no path
  occupant
- **AND** an accepted Chronicle binds its exact branch, head, merge base, tree,
  historical intent, useful invariants, rejected replay, and current semantic
  receiver
- **WHEN** native resolution re-observes the same ownerless target
- **THEN** the accepted disposition MAY be `lane_resolution/retire`
- **AND** ETHOS SHALL NOT create a recovery package merely to avoid semantic
  judgment
- **AND** any renewed owner, identity drift, Chronicle drift, or occupancy SHALL
  block the effect.

#### Scenario: diverged clean source uses a transient exact bridge after native accepted-ancestor no-effect

- **GIVEN** accepted semantic evidence selects direct retire for an exact clean
  ownerless lane
- **AND** native accepted-ancestor admission rejects the effect without mutation
  because the diverged source is not an accepted ancestor
- **WHEN** a later accepted reconciliation selects
  `lane_resolution/preserve-retire` for that same exact branch and head
- **THEN** the package SHALL be a transient content-addressed effect bridge and
  SHALL NOT reverse the semantic absorption judgment
- **AND** no bypass of native accepted-ancestor admission, raw Git deletion, or valid-owner takeover is authorized
- **AND** package clear SHALL require a later accepted binding to the exact
  decision ID and manifest SHA-256.

#### Scenario: dirty post-lease implementation is preserved after semantic review

- **GIVEN** a linked ownerless lane contains staged or unstaged tracked bytes
- **AND** isolated reconstruction proves the exact status, cached patch, working
  patch, and resulting full-index patch digests
- **WHEN** accepted evidence records which invariants are absorbed and why direct
  product replay is rejected
- **THEN** native `preserve-retire` SHALL verify and preserve all exact dirty
  bytes before removing only the named branch and worktree
- **AND** package clear SHALL require a separate accepted exact-manifest carrier.

#### Scenario: valid-owner semantic receiver remains protected

- **GIVEN** a valid-owner successor contains exact or stronger implementations
  of some absorbed invariants
- **WHEN** an ownerless remainder carrier cites that successor as read-only
  semantic evidence
- **THEN** the citation SHALL mint no ownership, mutation, land, retirement,
  cleanup, or completion authority over the valid-owner lane.

#### Scenario: transient clean bridge packages are cleared only by accepted exact manifests

- **GIVEN** accepted reconciliation authorized transient
  `lane_resolution/preserve-retire` for exact clean ownerless lanes only after
  direct retirement reached a no-effect boundary
- **AND** native effects removed the exact branches and worktrees while retaining
  verified packages with empty tracked and index patches
- **WHEN** a separate accepted successor binds each exact decision ID,
  completion receipt, manifest SHA-256, and repository bundle SHA-256
- **THEN** each package MAY be cleared only through its own native
  `lane_resolution/clear-preservation` invocation
- **AND** native clear SHALL re-read inventory and manifest bytes, remove only
  the named package, retain the immutable decision and completion receipt, and
  emit a durable clear receipt
- **AND** a changed manifest, duplicate package, missing receipt, wildcard clear,
  raw deletion, fourth package, or valid-owner mutation SHALL remain blocked.

### Requirement: Native ownerless closeout authority is consumed at the effect boundary

ETHOS SHALL retire a clean linked ownerless Work Lane only when its native effect
executor validates the immutable decision and Chronicle, configured Work Lane
role, exact Git worktree registration and incarnation, clean ownerless
coordination state, accepted ancestry, and a complete fence-held re-observation.
It SHALL execute a no-force worktree removal and accepted-ref-bound exact target
deletion CAS, verify all postconditions, and only then issue a provider-neutral
completion receipt. No external verifier, adapter response, predecessor record
root, or compatibility alias SHALL be required for current authority.

#### Scenario: exact ownerless target is retired natively

- **GIVEN** an immutable decision and Chronicle name one clean ownerless Work
  Lane whose branch has the configured Work Lane role
- **AND** Git registration, path, HEAD, incarnation, accepted ancestry, lease,
  Claim, holder, and target digests match the decision
- **WHEN** ETHOS acquires the exact target fence and the complete observation
  remains unchanged
- **THEN** ETHOS SHALL verify the accepted ref, remove the registered worktree
  without force, delete the exact target ref through CAS, and verify explicit
  ref, registration, path, coordination, decision, and fence postconditions
- **AND** it SHALL write the immutable completion receipt only after those
  postconditions pass.

#### Scenario: decision or Chronicle replacement is rejected

- **GIVEN** effect or completed-effect recovery admitted one decision snapshot
  and its bound Chronicle
- **WHEN** either file bytes, digest, disposition, lane identity, or observation
  binding changes before effect or recovery verification
- **THEN** ETHOS SHALL reject the transition before any new Git, worktree,
  fence, reservation, cleanup, or receipt effect.

### Requirement: Preserve-retire consumes one accepted target-bound Chronicle

For `lane_resolution/preserve-retire`, ETHOS SHALL read the Chronicle from the
configured accepted control checkout, not the invoking Work Lane. Its root-bound
working bytes SHALL be byte-identical to the exact accepted-tree regular blob and
to the decision digest. Its UTF-8 front matter SHALL contain exactly one
`event: lane_resolution/preserve-retire`, exactly one `target_head` equal to the
observed target HEAD, and exactly one target selector: either `target_branch`
equal to the observed branch or `target_branch_sha256` equal to the SHA-256 of
that branch's UTF-8 bytes. ETHOS SHALL revalidate those facts before receipt
reservation or preservation and again after package verification before worktree
or ref removal.

#### Scenario: one accepted preserve-retire Chronicle binds one target

- **GIVEN** a caller requests `preserve-retire` for one exact Work Lane
- **WHEN** the Chronicle lacks, replaces, duplicates, or mismatches its required
  event, selector, target HEAD, accepted bytes, or decision digest
- **THEN** ETHOS SHALL block the decision or apply before destructive retirement
- **AND** the Chronicle SHALL NOT authorize another branch or HEAD.

#### Scenario: post-preservation Chronicle drift blocks removal

- **GIVEN** ETHOS has verified one preservation package for an admitted target
- **WHEN** the target-bound Chronicle or target observation differs before
  worktree or ref removal
- **THEN** ETHOS SHALL retain the source branch and worktree
- **AND** it SHALL retain the verified package as governed recovery material
- **AND** it SHALL write only a `preserved_retirement_blocked` receipt with the
  exact permitted blocker and SHALL NOT record retirement.

#### Scenario: configured Work Lane role is authoritative

- **GIVEN** repository policy configures a Work Lane branch prefix other than
  the product default
- **WHEN** an exact registered branch satisfies that configured role
- **THEN** ownerless admission SHALL accept the role without hard-coded branch
  spelling
- **AND** a branch outside the configured role SHALL be rejected.

#### Scenario: late coordination or accepted drift blocks zero effect

- **GIVEN** native preflight observed an ownerless target
- **WHEN** a lease, Claim, holder, accepted-head change, decision change, path
  change, target change, or competing reservation wins before the fence-held
  observation is consumed
- **THEN** ETHOS SHALL perform no Git or worktree effect and SHALL report the
  exact blocking binding without minting ownership.

#### Scenario: accepted ancestry is required

- **GIVEN** the exact target and accepted HEAD are observable
- **WHEN** the target HEAD is not an ancestor of the accepted HEAD or ancestry
  cannot be verified
- **THEN** ETHOS SHALL reject ownerless retirement before effect.

#### Scenario: worktree-remove and ref inspection are three state

- **GIVEN** the exact ref transaction is prepared
- **WHEN** worktree removal, target-ref inspection, or fence inspection reports
  present, absent, or unverifiable state
- **THEN** only the state required by the current phase SHALL pass
- **AND** an error, malformed payload, or exception SHALL remain visible as a
  partial or unknown transition rather than being treated as absence.

#### Scenario: worktree-remove failure is classified by re-observation

- **GIVEN** the exact ref transaction is prepared for one target
- **WHEN** no-force worktree removal returns non-zero
- **THEN** ETHOS SHALL re-read the exact target ref, worktree registration, and
  path
- **AND** it SHALL retain `reserved_no_effect` only when all three remain
  unchanged, classify removed-registration with a present ref as
  `worktree_removed_ref_present`, and classify any other uncertain combination
  as `transition_unknown`.

#### Scenario: zero-effect retry may rebind a descendant accepted head

- **GIVEN** one exact reservation remains `reserved_no_effect`, the same
  decision, executor, target, registration token, and coordination bindings still
  hold, and no Git or worktree effect occurred
- **WHEN** exact pre-fence admission classifies that reservation as the same
  zero-effect retry and the current accepted HEAD equals or descends from the
  reserved accepted HEAD
- **THEN** ETHOS SHALL release the old exact fence and reservation, acquire a
  fresh exact fence, and complete the full under-fence re-observation before
  persisting a new reservation or starting effect
- **AND** divergence, target drift, decision drift, registration drift, or
  unverifiable state SHALL block without effect.

#### Scenario: current record authority is isolated from history

- **GIVEN** predecessor records remain in historical accepted or worktree roots
- **WHEN** ETHOS decides, applies, recovers, writes a receipt, clears, or
  inventories current lane-resolution state
- **THEN** it SHALL access only the versioned current record root
- **AND** history SHALL NOT create a conflict, authorize an effect, or be
  deleted by current cleanup.

#### Scenario: decision-only records are visible

- **GIVEN** a valid current decision exists without a manifest, receipt, clear
  record, or reservation
- **WHEN** current inventory runs
- **THEN** it SHALL include the decision identifier, report
  `state=decision_pending`, and increment decision and pending-decision counts.

#### Scenario: invalid current payload blocks

- **GIVEN** any payload is present in the versioned current record root
- **WHEN** its typed contract, version, canonical bytes, or cross-field
  invariant is invalid
- **THEN** current inventory and effect admission SHALL report a blocking
  integrity gap and SHALL NOT silently ignore the payload.

#### Scenario: current records use explicit provider-neutral versions

- **WHEN** ETHOS writes a new completion receipt, ownerless reservation, or clear
  receipt
- **THEN** it SHALL write receipt schema version 3, reservation schema version
  2, and clear schema version 1
- **AND** the ownerless binding SHALL contain only executor, decision digest,
  accepted branch and HEAD, target digest, target-binding digest, and
  postcondition digest.

#### Scenario: receipt-present cleanup is effect free

- **GIVEN** the exact immutable completion receipt is durable and cleanup is
  incomplete
- **WHEN** the same decision retries
- **THEN** ETHOS SHALL validate the exact decision, lane, head, receipt,
  postconditions, fence, and reservation binding and perform only idempotent
  cleanup
- **AND** it SHALL NOT repeat Git/worktree effect, rewrite the receipt, consult
  historical roots, or recreate effect authority.

#### Scenario: successful cleanup preserves ordering

- **GIVEN** the exact immutable completion receipt is durable
- **WHEN** ETHOS cleans ownerless coordination
- **THEN** it SHALL release the exact SQLite fence through compare-and-swap
  before deleting the visible ownerless reservation
- **AND** a failed or unverifiable fence release SHALL retain the visible
  reservation.

#### Scenario: effect-complete recovery precedes ordinary observation

- **GIVEN** the reservation state is `effect_complete_receipt_missing`
- **WHEN** the same decision retries
- **THEN** ETHOS SHALL recover or validate the exact completion receipt before
  ordinary lane observation
- **AND** it SHALL NOT depend on observing a worktree already removed by the
  completed effect.

#### Scenario: dangling path and post-CAS exception fail closed

- **GIVEN** ownerless effect or postconditions are being evaluated
- **WHEN** the target path is a dangling symlink or an ordinary exception occurs
  after the CAS boundary
- **THEN** the path SHALL remain present for safety evaluation
- **AND** the exception SHALL become `transition_unknown` with explicit
  reconciliation required.

#### Scenario: damaged fence payload preserves independent lease truth

- **GIVEN** the lease and closeout-fence stores are independently current
- **WHEN** one fence payload cannot be decoded or validated
- **THEN** state inventory SHALL report the fence projection as unverifiable
- **AND** it SHALL continue to report independently validated lease facts rather
  than rewriting the lease schema state as invalid.

#### Scenario: undeclared external lifecycle execution is rejected

- **GIVEN** the Work Lane lifecycle declares its allowed executable and state
  bindings
- **WHEN** a mandatory admission or effect path invokes an undeclared external
  executable
- **THEN** generic coupling audit SHALL fail before proof or land
- **AND** optional explicitly configured semantic-attestation and policy adapters
  outside lane-resolution effect authority SHALL remain unaffected.

### Requirement: Interrupted accepted-worktree synchronization recovery is receipt-bound

ETHOS SHALL provide one explicit recovery path for a native closeout that
already promoted the accepted ref but failed while synchronizing that same
checkout. The path SHALL not weaken ordinary dirty accepted-root admission or
advance a ref, lease, proof record, SQLite state, retired-resolution record, or
ownerless resolution record.

#### Scenario: Exact interrupted residue is recovered by a current candidate runner

- **WHEN** `ethos land --closeout --recover-accepted-worktree-sync --apply`
  receives authorization, stale-lock and irreversible confirmation, an external
  failed-closeout receipt and SHA-256, an expected promoted accepted head, an
  exact index-lock digest, and an absent external quarantine path
- **THEN** it SHALL require the receipt to record
  `accepted_worktree_sync_failed` for the configured accepted/candidate
  branches and exact prior/promoted heads
- **AND** it SHALL require accepted `HEAD` and the accepted ref to equal the
  receipt's promoted head, while the candidate ref equals that head or is its
  descendant and the index/worktree exactly equal the prior accepted tree with
  no untracked or conflicted content
- **AND** it SHALL relocate only the verified regular lock through an atomic
  no-replace same-filesystem operation, synchronize only the accepted worktree,
  and re-observe clean checkout and unchanged refs
- **AND** it SHALL fail closed if the native no-replace operation is unavailable
  or the quarantine target races into existence.

#### Scenario: Ordinary dirty accepted-root work remains blocked

- **WHEN** an accepted root is dirty but lacks the exact receipt-bound prior
  index/worktree residue, or any receipt/head/digest/fingerprint/quarantine
  binding differs
- **THEN** recovery SHALL block with a specific gap
- **AND** ordinary `ethos land --closeout` SHALL continue to report
  `accepted_root_dirty`
- **AND** no hard reset, quarantine relocation, or ref mutation SHALL occur.

### Requirement: Clean ownerless divergence distinguishes retained lineage from unique intent

ETHOS SHALL require an accepted, target-bound semantic judgment before retiring
any clean linked Work Lane that has no current lease or Claim and is diverged
from accepted truth. The judgment MUST distinguish history retained by an exact
valid-owner descendant from unique intent that requires a verified preservation
package, and it SHALL grant no authority over the valid-owner lane.

#### Scenario: exact predecessor history remains reachable from valid-owner descendants

- **GIVEN** a clean missing-lease predecessor has an exact branch and HEAD
- **AND** fresh Git observation proves that HEAD is an ancestor of every named
  valid-owner semantic receiver
- **WHEN** accepted Chronicle evidence selects `lane_resolution/retire`
- **THEN** native resolution SHALL recheck the predecessor and descendant
  containment without mutating any valid-owner lane
- **AND** any accepted-ancestor effect boundary SHALL block without source
  deletion and require a separate accepted reconciliation before a changed
  disposition.

#### Scenario: unique clean divergence is preserved before retirement

- **GIVEN** a clean missing-lease lane contains committed intent reachable from
  no other branch or tag
- **AND** accepted truth does not adopt that intent
- **WHEN** accepted Chronicle evidence selects
  `lane_resolution/preserve-retire`
- **THEN** ETHOS SHALL create and verify the exact recovery package before
  removing only the named source branch and worktree
- **AND** preservation SHALL NOT claim semantic acceptance, remote publication,
  or authority to clear the package.

#### Scenario: valid-owner or dirty state remains protected

- **WHEN** fresh observation finds a valid lease, Claim-bound owner, dirty
  overlay, changed HEAD, changed registration, or lost descendant containment
- **THEN** housekeeping and exceptional resolution SHALL leave that lane intact
- **AND** the outcome SHALL remain a bounded blocker rather than a cleanup
  success claim.
