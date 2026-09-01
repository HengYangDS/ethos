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

### Requirement: Official OpenSpec Governance
ETHOS SHALL keep `openspec/` as an official repository governance capability for
spec-driven planning and change records while preserving `ethos ...` as the
public product command plane.

OpenSpec remains mandatory governance, not a product substrate and not a second command plane.
ETHOS status is the singular reader for repository readiness.

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
- **WHEN** `ethos prove --gate repository-audit --json` runs
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
- **WHEN** `ethos prove --gate repository-audit --json` runs
- **THEN** the canonical repository audit verifies each current standard adapter
  against its declared boundary, lifecycle, contracts, fallback, and retirement
  behavior

### Requirement: Product Design Contract

ETHOS SHALL keep exactly two canonical design authorities: the product design
contract SHALL own product meaning and terminal invariants, and the terminal
governance product design SHALL own the current dependency order, acceptance
boundaries, re-planning triggers, and terminal exit condition. Official OpenSpec
Changes SHALL own bounded intent and task progress; archived Changes SHALL remain
history and SHALL NOT own the current implementation queue.

#### Scenario: Design contract is audited

- **WHEN** repository architecture proof inspects current governance design
- **THEN** the product design contract and terminal governance product design
  are present
- **AND** the product contract contains the accepted semantic, lifecycle,
  projection, recovery, operational-resource, documentation, and evidence-plane
  invariants
- **AND** the terminal plan contains the complete current convergence order and
  the acceptance boundary for each bounded successor Change
- **AND** adopter observations are treated as bounded comparison evidence, not
  as a design authority or a source to copy or mutate
- **AND** neither document delegates current truth to an archived task list,
  conversation history, feedback registry, or parallel roadmap

#### Scenario: Design state is distinguished from implementation state

- **WHEN** a terminal invariant is documented before its executable owner has
  passed acceptance
- **THEN** the terminal plan identifies that work as an unclosed implementation
  batch
- **AND** the contract, status, and completion report do not claim that source,
  hosted CI, signatures, publication, runtime installation, or adopter
  conformance is already complete

#### Scenario: Superseded design advice is reconciled

- **WHEN** recovered guidance conflicts with a later accepted invariant
- **THEN** only the current invariant remains normative in the two canonical
  design authorities
- **AND** obsolete carrier advice is not restored as compatibility state,
  duplicated prose, or another tracked schema

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

### Requirement: Parity evidence is committed before Work Lane proof

ETHOS SHALL treat stale configured generic parity evidence as an explicit
evidence-freshness proof gap. A Work Lane that changes the parity-relevant tree
shall refresh and commit its parity evidence before it executes proof or lands.

#### Scenario: parity-relevant Work Lane source makes generic evidence stale

- **GIVEN** a Work Lane has committed a parity-relevant source or contract change
- **AND** its tracked generic parity evidence no longer matches the resulting
  parity-relevant semantic tree
- **WHEN** `ethos prove --gate evidence-freshness --json` or executed proof evaluates
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

#### Scenario: Governance context is shared in audit and proof payloads

- **WHEN** ETHOS emits audit or proof payloads for any governed repository
- **THEN** the payload includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** `status` is the singular read-only readiness command
- **AND** profile or adapter differences do not create a second product command
  plane
- **AND** first-glance product docs name this as Isomorphic Governance without
  turning governed repositories into product clones.

#### Scenario: Primary command results expose the shared governance context

- **WHEN** ETHOS emits `status`, `plan`, `prove`, `land`, or `publish` JSON for any
  governed repository
- **THEN** the top-level result includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** `status` remains the singular read-only readiness command
- **AND** profile or adapter differences do not create a second product command
  plane
- **AND** command-specific `data` payloads remain governed by their own native
  schema or domain contract rather than becoming a second truth store.

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names, and SHALL use one explicit rule for
documentation roots, onboarding placement, and README necessity. The physical
shape of ETHOS's own docs is a product projection; adopter repositories retain
their native subject layout under the portable Docs Registry contract.

#### Scenario: Common docs kernel is audited

- **WHEN** documentation governance audits the repository
- **THEN** it requires only the common semantic kernel owned by the current
  contract: the documentation root, evidence, history, and reference lanes
- **AND** product extension roots are retained only when they contain a distinct
  subject or function
- **AND** no extension root is mandatory for an adopter merely because ETHOS
  uses it

#### Scenario: First-run guidance is placed by function

- **WHEN** ETHOS has one first-run onboarding document
- **THEN** it SHALL live under the `guides` function root as `docs/guides/quickstart.md`
- **AND** links, stable-path metadata, taxonomy metadata, registry output, and
  command examples SHALL resolve to that path
- **AND** the former onboarding root SHALL not remain as a historical habit or
  redirect root

#### Scenario: A documentation directory needs a README

- **WHEN** a documentation directory is evaluated for a README
- **THEN** a README SHALL exist only when it provides real navigation, a
  semantic boundary, or an index for multiple meaningful children
- **AND** a directory with one substantive document SHALL not receive a
  placeholder README merely because the directory exists
- **AND** an empty directory or `.gitkeep` SHALL be removed

#### Scenario: Documentation taxonomy is projected

- **WHEN** the Docs Registry reads the ETHOS documentation tree
- **THEN** role, state, subject, and relation metadata are validated by the
  registry owner and directory names express subject/function rather than
  lifecycle state
- **AND** the registry SHALL report every broken link, stale stable path,
  unindexed document, duplicate subject, and invalid README disposition

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and does
  not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order,
  contracts, evidence, claims, and proof rather than by directory name
- **AND** unlanded intent belongs in OpenSpec changes, plans, research, or
  decision revisit triggers rather than in a generic intent directory

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, guides, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

### Requirement: Release Policy

ETHOS SHALL expose a release policy report covering version alignment, hosted
profile surfaces, protected branch/tag expectations, attestation formats,
publication topology, and the executable local verification/install owners
declared by that topology.

#### Scenario: Release policy is complete

- **WHEN** `ethos publish --json` runs in the ETHOS repository
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
- **AND** `verdict` SHALL be `block`.

#### Scenario: Local owner cannot escape the repository

- **WHEN** a declared local command is absolute, contains a traversal that
  resolves outside the repository, or follows a link outside the repository
- **THEN** release policy SHALL report a path-escape required gap
- **AND** it SHALL NOT inspect or execute the outside target as a release owner.

### Requirement: Release Attestation
ETHOS SHALL bind a standard SBOM to the exact built artifact without inventing
local provenance or signature authority.

#### Scenario: Built artifact SBOM is generated
- **WHEN** `uv run --frozen --offline python -m nox -s supply_chain` runs
- **THEN** the policy-owned Syft release emits SPDX 2.3 JSON for exactly one built wheel
- **AND** the receipt binds HEAD, artifact and SBOM digests, and generator version
- **AND** no provenance, signature, SLSA level, hosted-CI, or publication claim
  exists without its own provider receipt.

### Requirement: Commit And Hosted Verification Policy
ETHOS SHALL distinguish current local commit/signature status from GitLab
service-side verification status without requiring tracked historical alias
metadata.

#### Scenario: Current commit policy is audited
- **WHEN** `tools/ci/scripts/run-head-bound-proof.sh` runs
- **THEN** the result reports local identity, subject, and signature gaps
  without inferring GitLab verification from local Git output

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
- **THEN** it writes repository-common `gc.packRefs=false` and blocks installation if that
  maintenance policy cannot be recorded
- **AND** it removes worktree-local `gc.packRefs` and `core.hooksPath` overrides
  so every linked worktree inherits the same activation
- **AND** the hook applies its existing fail-closed admission to every raw
  accepted transaction rather than guessing that a physical ref rewrite is safe
- **AND** a manual `pack-refs` is not classified as an authorized closeout.

### Requirement: OpenSpec Lifecycle Contract Review

ETHOS SHALL compose official OpenSpec validation with one transient Commitment
compiled from each selected active Change. Official proposal, specs, design,
tasks, metadata, and configuration are the sole tracked intent and lifecycle
carriers; no `commitment.toml`, `scope.toml`, local template, or Change README is
required.

#### Scenario: Active OpenSpec Change is lifecycle complete

- **GIVEN** an active OpenSpec Change has every artifact required by its official schema
- **WHEN** ETHOS audits lifecycle or compiles a plan
- **THEN** it validates the official Change and deterministically compiles acceptance intent
- **AND** no parallel tracked carrier participates

#### Scenario: Active OpenSpec Change lacks its contract

- **WHEN** an official required artifact is missing, invalid, or incomplete
- **THEN** ETHOS reports the exact official artifact or task gap
- **AND** no bootstrap, claim, archive scan, or parallel metadata grants authority

### Requirement: Reference Adopter Parity Closure
ETHOS SHALL prove reference adopter parity through generic profile and shadow
evidence mechanisms rather than product-runtime adopter terms.

#### Scenario: Reference adopter parity is closed
- **GIVEN** tracked parity evidence for a reference adopter reports `verdict=pass`
- **AND** the evidence covers OpenSpec claims trust review, Work Lane
  lifecycle, proof evidence, and profile boundaries
- **WHEN** ETHOS reports parity gaps for that adopter
- **THEN** no covered capability gap is emitted for that adopter
- **AND** product runtime packages remain free of adopter-private terminology

### Requirement: Contextual Authority Resolution
ETHOS SHALL resolve authority and currentness for the exact subject, predicate,
scope, plane, validity, and bindings without a persisted graph, rank, current
pointer, directory status, or manual index.

#### Scenario: independent planes report different states
- **WHEN** local proof passes while a configured forge has no hosted Attestation
- **THEN** local proof is current only for its local plane and hosted state remains unknown

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
- **AND** detached replay for accepted, candidate, proposal, other, or unknown
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
  proposal, other, and unknown detached branches remain protected and fail closed

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

### Requirement: Agent Invocation Admission Boundary

ETHOS SHALL evaluate mutation-capable invocation as an action-specific request
over applicable Commitments, current repository facts, and bounded Evidence.
Authority SHALL rank truth sources rather than act as an identity or permission
engine. Intent and confirmation flags, holder labels, identity assertions, and
prior decisions SHALL NOT become reusable authorization by themselves.

#### Scenario: mutation decision is exact-request bound

- **WHEN** ETHOS evaluates a mutation request
- **THEN** it returns `pass`, `block`, or `unknown` with `why`, `next`, and
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

### Requirement: Work Lane Coordination Read Model

The coordination reader SHALL derive current lane views from Git facts, the
selected Commitment, local Lease fencing, and exact Attestation queries. It
SHALL NOT expose shared-inbox acknowledgement, consumed state, cursor, mutable
selection, or inbox digest as lifecycle or progress authority.

#### Scenario: Concurrent input exists

- **WHEN** input occurrences are present in the Attestation set
- **THEN** status may project their immutable identities and selected
  dispositions
- **AND** absence of an acknowledgement or mutable inbox flag creates no hidden
  progress state

#### Scenario: foreign lane preview remains observe-only

- **WHEN** status sees a foreign Work Lane
- **THEN** it projects observed facts without mutation authority
- **AND** visibility grants no handoff, land, or retirement right

#### Scenario: bounded readers defer foreign path scopes

- **WHEN** detailed foreign path inspection is outside the bounded read
- **THEN** the reader marks detail deferred
- **AND** it does not infer overlap or safety

#### Scenario: projection preserves observed coordination detail state

- **WHEN** a bounded reader emits coordination detail state
- **THEN** summary and payload agree on that state
- **AND** no inbox counter substitutes for direct observation

#### Scenario: normalized lease has one concrete current holder

- **WHEN** a valid current Lease is projected
- **THEN** it names one concrete holder and generation
- **AND** no shared-inbox consumer identity replaces the holder

#### Scenario: lease generation detects but does not claim hard fencing

- **WHEN** a Lease generation is current
- **THEN** it detects stale local mutations and coordinates writers
- **AND** it does not claim distributed or provider fencing

#### Scenario: lease and Git lifecycle is crash-consistent

- **WHEN** a coordinated transition is interrupted
- **THEN** exact receipt and observed Git/Lease states determine recovery
- **AND** no mutable inbox state determines success

#### Scenario: legacy adoption and cleanup resist replay

- **WHEN** retired coordination bytes are encountered
- **THEN** current readers ignore them as authority
- **AND** they cannot be replayed through compatibility discovery

#### Scenario: cross-host handoff creates destination-local coordination

- **WHEN** an exact handoff is accepted on another host
- **THEN** the destination creates its own local Lease generation
- **AND** an acknowledgement is evidence only, not lifecycle state

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

Routine lifecycle SHALL remain mechanically derived from current facts and exact
plans. Exceptional interpretive judgment SHALL be an exact, non-authorizing
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing and postcondition Attestations
- **AND** no tracked decision record is required

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** an exceptional destructive operation requires human judgment
- **THEN** a separately accepted Commitment and bound decision Attestation name
  exact target, evidence, disposition, recovery, and validity
- **AND** the operation re-observes mutable facts before its first effect

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, Lease, content, or recovery status is unknown or dirty
- **THEN** ETHOS preserves or blocks rather than inferring authority
- **AND** irreversible deletion requires exact accepted judgment and evidence

#### Scenario: break-glass reconciles after emergency action

- **WHEN** a predeclared break-glass Commitment admits an emergency effect
- **THEN** the result is an exact Attestation and later integration remains
  blocked until accepted reconciliation
- **AND** a self-supplied flag or holder string is insufficient

#### Scenario: lane handoff is recorded as Chronicle resolution

- **WHEN** an exceptional handoff judgment is required
- **THEN** it is recorded as a decision Attestation, not Chronicle
- **AND** it does not replace the destination-local Lease

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **WHEN** a lane has missing or ambiguous holder evidence
- **THEN** orphan-like facts remain observations and accepted disposition is an
  Attestation
- **AND** no persistent orphan or Chronicle state is created

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **WHEN** exact accepted judgment and evidence admit retirement
- **THEN** the resolver re-observes the source and emits an effect Attestation
- **AND** the authority does not extend to another lane or remote effect

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
- **THEN** ETHOS recommends `uv run --frozen --offline python -m nox -s local_ci` as local
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

ETHOS SHALL expose non-blocking advisory governance signals in the bounded
status reader without treating them as transition-blocking required gaps.

#### Scenario: Status exposes advisory signal count and layer

- **WHEN** `ethos status --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** when there are advisory gaps but no required gaps status remains
  reports `verdict=pass` and `state=advisory` rather than `state=ready`
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Status exposes advisory signal count, layer, and one bounded next action

- **WHEN** `ethos status --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** top-level `next_action` selects one deterministic read-only inspection or explanation action for known advisory signals
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Status carries Work Lane coordination advisories

- **WHEN** `ethos status --json` runs and workspace status contains Work Lane coordination advisory gaps
- **THEN** the status summary includes those gaps in `advisory_gap_count`
- **AND** `gap_layers.advisory_signals.advisory_gaps` includes the Work Lane coordination advisories
- **AND** top-level `next_action` routes to one deterministic read-only coordination inspection command when no blocking gap is present
- **AND** the advisories do not become status `required_gaps`

#### Scenario: Status carries Work Lane coordination blockers

- **WHEN** `ethos status --json` runs for a product or adopter profile and workspace status contains required Work Lane coordination gaps
- **THEN** those required coordination gaps appear in status `required_gaps`
- **AND** `gap_layers.coordination_risk.required_gaps` carries the required coordination gaps
- **AND** `gap_layers.coordination_risk.advisory_gaps` carries advisory coordination signals without making them required
- **AND** product and adopter profiles both surface required coordination gaps as blockers
- **AND** status remains read-only and does not authorize foreign Work Lane cleanup

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
- **THEN** `uv build --out-dir build/artifacts/python --clear
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
`proposal/*`; `candidate/dev` and `work/*` remain local.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `proposal/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local candidate is excluded from hosted providers

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `proposal/*`
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

### Requirement: Declared publication peer topology

The repository SHALL declare zero or more publication peers explicitly. Each
peer SHALL have a unique peer ID and Git remote plus a provider label used only
to select a transport or observation adapter. Provider labels MAY repeat and
SHALL NOT create a primary peer, product identity, object producer, signing
authority, or dependency between peers. The locally existing Git object SHALL
be the sole publication source. Every peer SHALL be optional and independently
observed, updated, verified, retried, and attested.

#### Scenario: local-only publication remains valid

- **WHEN** valid local verification and installation are declared with no peers
- **THEN** the local publication lifecycle SHALL complete without remote observation
- **AND** it SHALL NOT claim hosted CI or remote publication

#### Scenario: independent remote observations remain no-push

- **WHEN** publish readiness observes one or more declared peers
- **THEN** it SHALL expose each target separately without pushing
- **AND** hosted CI status SHALL remain unclaimed unless separately evidenced

#### Scenario: publication is local only

- **WHEN** the peer collection is empty and both local commands are valid
- **THEN** topology and local publication readiness SHALL remain valid
- **AND** no remote observation or hosted claim SHALL be manufactured

#### Scenario: GitLab is the only declared peer

- **WHEN** exactly one GitLab peer is declared
- **THEN** publication SHALL observe and update only that peer
- **AND** it SHALL NOT require GitHub or infer a primary provider

#### Scenario: GitHub is the only declared peer

- **WHEN** exactly one GitHub peer is declared
- **THEN** publication SHALL observe and update only that peer
- **AND** it SHALL NOT require GitLab or infer a primary provider

#### Scenario: both remote peers are declared

- **WHEN** several peers have unique IDs and Git remotes
- **THEN** every peer SHALL receive the same selected local Git object
- **AND** no peer SHALL read, wait on, rewrite, or act as the source for another peer

#### Scenario: provider labels repeat

- **WHEN** several distinct peers use the same provider adapter
- **THEN** topology SHALL remain valid
- **AND** peer identity SHALL remain the declared ID and Git remote rather than the provider label

#### Scenario: peer identity is ambiguous

- **WHEN** two peers reuse an ID or Git remote
- **THEN** topology SHALL fail closed before remote observation or mutation

#### Scenario: retired and current declarations coexist

- **WHEN** peer tables coexist with a fixed provider publication scalar
- **THEN** topology SHALL fail closed as an ambiguous declaration

### Requirement: Strict remote publication admission

Publication admission SHALL resolve the complete target ref through one
provider-neutral contract:

```text
ref kind -> lifecycle role -> local source object -> allowed effect
```

The admitted kinds SHALL be accepted branch, release branch, proposal branch,
and annotated release tag. Candidate and Work Lane branches SHALL remain local
only. An annotated release tag matching the declared release-tag policy SHALL
have release-publication role and SHALL NOT be classified as branch role
`other`. Unknown refs, lightweight release tags, undeclared remotes, ambiguous
topology, untrusted local signatures, and refs outside the positive role set
SHALL fail closed before a writable remote effect.

#### Scenario: accepted and release branches are publishable

- **WHEN** a proved accepted object is selected for the declared accepted and release refs
- **THEN** both refs SHALL be eligible targets of one receipt-bound publication request
- **AND** each desired OID SHALL be the exact selected local commit OID

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** a proved candidate object is selected for a declared proposal ref
- **THEN** the proposal ref SHALL be eligible for publication
- **AND** candidate and Work Lane refs themselves SHALL remain remote-forbidden

#### Scenario: annotated release tag is classified positively

- **WHEN** a locally existing signed annotated tag matches the declared release-tag policy
- **THEN** `refs/tags/<tag>` SHALL resolve to annotated release tag and release-publication role
- **AND** it SHALL NOT emit `publication_remote_role_unavailable:other`

#### Scenario: tag is lightweight or untrusted

- **WHEN** a release-tag target is not an annotated tag object or its local signature is not trusted
- **THEN** publication SHALL fail before observing a writable remote effect
- **AND** it SHALL identify the exact object or trust gap

#### Scenario: non-canonical declaration fails closed

- **WHEN** publication configuration is missing, contains unknown fields, mixes retired scalar ownership with peers, or names an undeclared remote
- **THEN** admission SHALL fail closed
- **AND** it SHALL NOT infer `origin`, preserve a compatibility state, or bypass ref enforcement

#### Scenario: repository-only peer has no CI

- **WHEN** a declared peer omits both the `ci_cd` capability and `ci_surface`
- **THEN** local verification SHALL remain required
- **AND** hosted CI SHALL remain unclaimed without blocking repository publication

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

### Requirement: Preservation-bound exceptional Work Lane retirement

ETHOS SHALL preserve or preserve-retire a dirty foreign or ownerless Work Lane
only when a separately accepted Commitment requires the disposition and one
exact decision Attestation binds target, observation, recovery material,
validity, and actor. The operation SHALL re-observe every mutable fact before
its first effect.

#### Scenario: dirty residual lane is preserved without retirement

- **GIVEN** an exact decision Attestation selects preservation for one dirty lane
- **WHEN** a maintainer applies the accepted operation
- **THEN** ETHOS writes and verifies the digest-bound recovery package
- **AND** retains the exact branch and worktree

#### Scenario: dirty lane is preserved before retirement

- **GIVEN** an exact decision Attestation selects preserve-retire
- **WHEN** irreversible controls and fresh observations pass
- **THEN** ETHOS verifies recovery material before exact retirement
- **AND** emits one effect Attestation requiring reconciliation when partial

#### Scenario: ordinary dirty retirement remains blocked

- **WHEN** dirty retirement lacks the accepted Commitment and exact decision
  Attestation
- **THEN** ETHOS blocks without removing branch or worktree

#### Scenario: Chronicle disposition is bound before the effect

- **WHEN** a disposition is required before an exceptional effect
- **THEN** ETHOS binds one decision Attestation and its canonical identity
- **AND** no Chronicle path, mutable decision record, or supplied flag authorizes
  the effect

#### Scenario: detached dirty residue is normalized without changing bytes

- **WHEN** a detached historical worktree is prepared for exact resolution
- **THEN** ETHOS first captures HEAD, index, reflog, path, ownership, and content
  digests without changing bytes
- **AND** any reconstructed ref mints neither ownership nor effect authority

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
- **THEN** ETHOS SHALL report `verdict=block`, `state=partial_transition`, and
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

ETHOS SHALL invoke the repository-locked official `@fission-ai/openspec@1.11.0`
package from its declared local runtime and CI bootstrap. The effective package
identity SHALL derive from the repository package declaration and lockfile;
ambient npx, PATH, cache, and global versions SHALL not be accepted as a
fallback. Adoption SHALL NOT generate an OpenSpec workspace or provider CI
surface.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter and CI bootstrap
- **THEN** each repository-owned package invocation SHALL resolve the locked
  `@fission-ai/openspec@1.11.0` identity
- **AND** strict official OpenSpec validation SHALL remain the governance gate
- **AND** adoption SHALL plan no OpenSpec or CI carrier.

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
`--no-sync`.

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
- **AND** it does not resolve the retired root project environment interpreter

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
  hook, or CI projection containing an active retired root-environment fallback
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

- **WHEN** `ethos status --json` reads an accepted root with classified
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

### Requirement: Canonical declarations have a self-contained package projection

ETHOS SHALL package canonical system declarations without making a wheel build
depend on paths outside its source distribution.

#### Scenario: The Python wheel is built from its source distribution

- **WHEN** the `ethos` source distribution is unpacked for a wheel build
- **THEN** each packaged declaration is read from the sdist-local
  `src/ethos/data/` projection
- **AND** the wheel contains the corresponding `ethos/data/` resource
- **AND** the build does not require checkout-relative `system/` paths.

### Requirement: External-adopter profile evidence has a bounded durable record

A completed local external-adopter binding exercise SHALL be one Attestation
whose payload binds product revision, adopter revision, outcome, raw-bundle
digest, and publication boundary. Host-local raw material and provider state
remain evidence, not repository truth.

#### Scenario: Local profile evidence is promoted

- **WHEN** an isolated binding exercise completes
- **THEN** its Attestation binds exact revisions, outcomes, and raw-bundle digest
- **AND** explicitly states whether remote publication occurred

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** the Attestation proves only digest-bound observation
- **THEN** it does not claim semantic correctness, hosted execution, provider
  authority, or independent review
- **AND** it requires no named account, credential, key, daemon, or network

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
- **AND** the mutation verdict SHALL remain `unknown`
- **AND** the next action SHALL state that no push was performed

#### Scenario: Reachable but non-synchronized remote remains deferred

- **WHEN** the remote is available but the tracking comparison is not
  `synchronized`
- **THEN** `data.publication.remote_state` SHALL remain `deferred`
- **AND** the command SHALL not claim a remote push or hosted-CI result

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require every valid adopter declaration to carry a non-empty
`[openspec].material_paths` list. For changed paths matching that declaration,
prewrite, changed planning, and proof SHALL attribute the fresh paths to the same
single selected active official OpenSpec Change. The attribution is a fact, not
an authored scope or permission carrier.

#### Scenario: covered material path is admitted across all surfaces

- **GIVEN** exactly one valid active Change is selected
- **WHEN** prewrite, changed planning, or proof evaluates a declared material path
- **THEN** each surface reports the same Change attribution
- **AND** no parallel tracked carrier participates

#### Scenario: uncovered material path is rejected consistently

- **WHEN** no active Change can own a declared material path
- **THEN** every surface reports `openspec_active_change_missing`
- **AND** no proof gate or historical carrier substitutes for intent

#### Scenario: Commitment coverage is singular

- **WHEN** more than one active Change could own a declared material path
- **THEN** every surface reports the same ambiguous active-Change gap
- **AND** no `scope.toml`, Commitment field, archive, or unrelated Change authorizes the write

### Requirement: Accepted closeout remains candidate-first and non-self-approving

Accepted advance SHALL fast-forward to live candidate with candidate proof and
one-shot exact ref intent. Candidate-tree policy decides admission; accepted
hooks and CAS enforce it. With `release_mirror = "accepted_ff"`, both protected
refs advance atomically under that evaluator. A candidate replacement for the
reference-transaction hook SHALL be clean, executable, and transaction-local;
it SHALL NOT change global config or weaken raw admission. Otherwise configured
hooks remain.

#### Scenario: raw update-ref targets a proven candidate head

- **GIVEN** the candidate checkout is clean and has a complete proof for its
  live head
- **WHEN** a caller runs raw `git update-ref` to move the accepted branch to
  that head without an exact official ref intent
- **THEN** the accepted-ref hook SHALL reject the move
- **AND** candidate-tree evaluation SHALL not make the marker optional.

#### Scenario: Official accepted_ff closeout advances both protected refs

- **GIVEN** `dev` and `main` are atomically advanced by an official
  `accepted_ff` closeout to the live, proven candidate head
- **AND** the incumbent accepted checkout cannot run its hook reducer
- **WHEN** the armed reference-transaction hook prepares the transaction
- **THEN** it evaluates both transitions through the clean candidate runner
- **AND** it admits the transaction only when each exact ref intent and
  substantive candidate/proof check passes
- **AND** `dev` and `main` reach the same candidate head atomically.

#### Scenario: Raw accepted or release-mirror move remains blocked

- **GIVEN** an `accepted_ff` repository has a proven live candidate head
- **WHEN** raw Git attempts to move `dev` or `main` without its exact ref intent
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

### Requirement: Status distinguishes local publication and hosted observation state

ETHOS status SHALL expose local publication readiness and hosted provider
observation status as separate read-only projections without performing a
remote probe or minting proof, hosted-success, or publication authority.

#### Scenario: Current hosted observation is projected

- **WHEN** ethos status runs and the configured hosted observation artifact
  binds the current tracked head
- **THEN** status data SHALL include hosted_observation state, freshness,
  provider-state summary, and bounded observation gaps
- **AND** those gaps SHALL remain advisory rather than repository proof
  required_gaps
- **AND** hosted GitHub status claimed, hosted GitLab status claimed, and remote
  publication claimed SHALL remain false

#### Scenario: Hosted observation is missing invalid or stale

- **WHEN** the hosted observation artifact is missing, malformed, or bound to a
  different tracked head
- **THEN** status SHALL expose missing, invalid, or stale hosted observation
  state
- **AND** it SHALL provide a bounded next action to rerun the observation owner
  script
- **AND** status SHALL remain read-only

#### Scenario: Local publication readiness is projected

- **WHEN** ethos status summarizes current blockers and proof readiness
- **THEN** status data SHALL include a local_publication projection that
  distinguishes ready from blocked local state
- **AND** the projection SHALL list its local blockers
- **AND** remote publication claimed SHALL remain false
- **AND** the projection SHALL NOT replace the ethos publish transition verdict

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
direct source-measurement ceilings or integrity, evidence binding, or the
raw-reference-move guard.

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
- **AND** raw accepted-root moves without a matching one-shot ref intent
  SHALL remain blocked.

#### Scenario: closeout-policy remediation does not lower the acceptance bar

- **GIVEN** a Change introduces committed-profile closeout policy resolution
- **WHEN** it is prepared for candidate landing
- **THEN** it SHALL preserve candidate-tree policy resolution and the
  raw-reference-move guard
- **AND** it SHALL pass the existing proof floor without raising either terminal
  ceiling, narrowing Git-present or extensionless-executable carrier coverage,
  weakening canonicalization or independent disagreement checks, or
  reclassifying a required direct source-measurement gap
- **AND** regenerated evidence and later proof SHALL bind the corrective HEAD.

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

ETHOS SHALL select the checkout-bound semantic runtime interpreter for a
shadow-parity external command when that interpreter exists. It SHALL select
that runtime before a retired root-environment interpreter, so ignored migration
residue that cannot import ETHOS does not make a current Work Lane appear to
have an external command failure.

#### Scenario: Stale root environment does not block current parity

- **WHEN** a Work Lane has both the checkout-bound semantic runtime and a
  retired root project environment that lacks the ETHOS package
- **THEN** shadow parity invokes the checkout-bound runtime for its external
  command
- **AND** it can produce current parity evidence instead of reporting an
  `external_command_failed` gap solely because of the stale root environment.

### Requirement: Final declared-peer proposal absorption is proof-bound and non-destructive

When one or more declared peer proposal refs carry a final divergent patch,
ETHOS SHALL retain each exact observed proposal tip through ordinary merge
ancestry, execute local proof and governed local closeout before a protected
update, and delete a proposal ref only after its tip is an ancestor of accepted
truth and its own normal deletion dry-run is accepted.

#### Scenario: Inputs move after a historical carrier archive

- **WHEN** a historical carrier has been archived but the candidate or a
  configured proposal ref advances before its unresolved lifecycle stages run
- **THEN** ETHOS SHALL preserve that archive as historical evidence
- **AND** bind an active continuation to the same episode claim before a new
  merge, proof, closeout, remote update, or proposal deletion is attempted
- **AND** the continuation SHALL re-observe the current inputs and retain its
  newly observed proposal tip through ordinary merge ancestry.

#### Scenario: Divergent proposal patch is reconciled

- **WHEN** a configured remote proposal ref is not an ancestor of the current
  candidate head
- **THEN** an owner-bound, claim-bound Work Lane records its exact tip and
  integrates it with an ordinary merge
- **AND** the resulting proposed head retains both the candidate and proposal
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
- **AND** a proposal ref is deleted only after accepted ancestry and its own
  deletion dry-run are verified.

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

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

Before an exceptional unbound effect, ETHOS SHALL re-observe the exact target,
selected Commitment, decision Attestation, Lease, and protected refs. It SHALL
publish a no-clobber attempt, compare-delete only the expected ref, verify
postconditions, and record the result in the sole Attestation set.

#### Scenario: Current holder relinquishes one exact lease generation

- **WHEN** the exact current holder and generation satisfy the selected operation
- **THEN** ETHOS revokes only that Lease through native CAS
- **AND** re-observes all non-Lease bindings before ref deletion

#### Scenario: Lease relinquishment remains fail-closed

- **WHEN** the Lease is absent, foreign, malformed, stale, replaced, or
  head-mismatched
- **THEN** ETHOS leaves the source ref intact and reports the observed gap

#### Scenario: Apply deletes only the observed ref

- **WHEN** all exact bindings remain stable and compare-delete succeeds
- **THEN** the effect Attestation binds before/after observations and
  postconditions
- **AND** protected refs remain unchanged

#### Scenario: Observation or postcondition drifts

- **WHEN** target, evidence, Lease, protected refs, or postconditions drift
- **THEN** ETHOS reports a blocked partial result without deleting newer state

#### Scenario: Target-specific evidence remains vendor-neutral

- **WHEN** exceptional retirement evidence is evaluated
- **THEN** its authority is limited to the exact branch, head, and operation
- **AND** vendor, account, session, host, or another target cannot extend it

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

ETHOS SHALL bind candidate audit, signature, local or external proof admission,
prepared ref intent, exact compare-and-swap, post-image observation, and
Attestation to one observed candidate commit and tree. Dry-run and apply SHALL
consume the same typed resolution; Git hooks and other projections SHALL not
own a competing accepted-head decision.

#### Scenario: Candidate HEAD changes during or after closeout audit

- **WHEN** accepted-root closeout observes the candidate HEAD before audit
- **THEN** the audit receives that HEAD and tree as its claim binding
- **AND** closeout re-observes the candidate after audit and immediately before
  mutation
- **AND** any mismatch blocks proof admission and accepted-root movement.

#### Scenario: Exact external evidence is bound before admission

- **WHEN** a package-only caller supplies an external verification receipt for
  the candidate
- **THEN** ETHOS validates its commit, tree, action, proof-floor digest, policy
  digest, implementation digest, issuer, key, signature, and validity against
  the exact closeout subject
- **AND** stale, failed, forged, wrong-subject, wrong-role, or wrong-verifier
  evidence fails closed
- **AND** a valid receipt remains an admission fact and never mints mutation
  authority.

#### Scenario: Local-only profile admits without Forge facts

- **WHEN** the repository profile declares no Forge peer and local proof is the
  selected proof plane
- **THEN** the same closeout transaction admits the exact locally proved signed
  candidate head
- **AND** no hosted receipt, provider status, or remote truth is fabricated.

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

### Requirement: Repository profile is a strict current binding
ETHOS SHALL validate repository profiles directly through one typed current binding.
Unknown, malformed, or incompatible data SHALL fail without normalization,
reinterpretation, or synthesized declarations.

#### Scenario: Former envelope and invalid root remain blocked
- **WHEN** a repository profile contains former envelope fields, including
  `schema_version`, `profile_version`, `ethos_contract_version`, or
  `[repository]`, or declares `roots.rules = "."`
- **THEN** ETHOS SHALL report
  `repository_profile_invalid:.ethos/profile.toml`
- **AND** it SHALL not silently ignore, normalize, or reinterpret the data
- **AND** it SHALL not synthesize `normative_sources`.

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

### Requirement: Invalid repository profile commands return structured blocks
Every public ETHOS reader, planning, proof, landing, publication, and OpenSpec
lifecycle command SHALL return a structured `EthosResult` when the target
repository profile is invalid. The result SHALL contain the stable invalid-profile
gap and SHALL not emit an uncaught traceback as its command result.

#### Scenario: JSON reader observes an invalid profile
- **WHEN** `ethos status --json` targets an invalid repository profile
- **THEN** it SHALL emit parseable JSON with `verdict = block`
- **AND** `required_gaps` SHALL contain
  `repository_profile_invalid:.ethos/profile.toml`.

#### Scenario: Enforcing proof command observes an invalid profile
- **WHEN** `ethos prove --json` targets an invalid repository profile
- **THEN** it SHALL emit parseable blocked JSON and exit non-zero
- **AND** it SHALL not start a mutation or create proof evidence.

#### Scenario: Landing does not mask an invalid adopter profile
- **WHEN** `ethos land --json` targets an invalid repository profile
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
- **THEN** the tracked record SHALL omit host-local paths, adopter-private
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
verifies the accepted ref. If a prior failed retirement preserved the exact
Work Lane ref and valid Lease but left its worktree absent, superseded
retirement MAY accept one explicit recovery path. It SHALL revalidate the exact
ref, HEAD, tree, Commitment, Lease generation, holder, actor, path absence,
worktree registration, and absorption authority before recreating that one
branch-bound worktree through the native worktree effect. It SHALL then resume
the same linked retirement transaction. A blocked later effect SHALL preserve
the recovered linked worktree or report its exact compensation failure.

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
- **AND** no wrapper, re-export, compatibility summary, or parallel Python
  effect remains.

#### Scenario: exact partial retirement state recovers and retires

- **GIVEN** a `work/*` ref remains at the Lease-bound expected HEAD and tree
- **AND** its valid Lease is held by the invoking actor
- **AND** the prior linked path is absent and not registered or reused
- **AND** accepted truth exactly absorbs the lane semantics
- **WHEN** the owner supplies that path to authorized superseded retirement
- **THEN** dry-run reports recovery and retirement readiness without mutation
- **AND** apply recreates the exact linked worktree and resumes the existing
  linked retirement effect
- **AND** terminal success requires the Lease, ref, and worktree all absent.

#### Scenario: partial recovery coordinates drift

- **WHEN** the path collides, the ref moves, the Lease or tree changes, the
  Commitment cannot be verified, or the actor is not the current holder
- **THEN** ETHOS blocks before recreating a worktree
- **AND** it preserves the current ref and Lease unchanged.

#### Scenario: retirement blocks after recovery

- **WHEN** exact worktree recovery succeeds but the subsequent ref transaction
  or Lease closeout blocks
- **THEN** ETHOS leaves the exact recovered linked worktree available for the
  normal public retry path
- **AND** it reports the failing transition and observed native carrier states
  without claiming retirement.

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

ETHOS SHALL reject a Work Lane start when its target path or ref already exists.
It SHALL initialize one detached candidate-based carrier, derive the final HEAD
from exact source commit metadata, acquire the Lease for that HEAD, and then
compare-and-create the ref. Failure compensation SHALL remove only proven
attempt-owned carriers and revoke the Lease only after their absence is proven.

#### Scenario: Target carrier already exists

- **WHEN** the requested target path or lane ref exists before initialization
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

#### Scenario: Foreign ref appears during failed creation

- **WHEN** lane ref compare-and-create fails and a same-name foreign ref is then
  observed
- **THEN** ETHOS does not delete that ref
- **AND** retains the Lease because carrier absence is not proven.

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
parity conflicts through the parity projection path; every other semantic conflict
remains blocked for explicit resolution.

#### Scenario: Historical one-off conflict shape reappears

- **WHEN** a rebase conflict matches a retired Claim-specific file set
- **THEN** ETHOS does not auto-resolve it from the historical Claim or archive
- **AND** the generic current conflict rules either resolve it or fail closed.

### Requirement: Ownerless closeout admission is consumed at the effect boundary

ETHOS SHALL retire a clean linked ownerless Work Lane only when the executor
recomputes the exact selected Commitment, decision Attestation, observations,
accepted relation, and local fencing. It SHALL perform no force operation and
write one completion Attestation only after exact postconditions pass.

#### Scenario: exact ownerless target is retired

- **WHEN** target, accepted head, decision, observation, occupancy, and fence
  remain exact
- **THEN** ETHOS performs only the admitted worktree/ref effects
- **AND** records completion after explicit absence checks

#### Scenario: decision snapshot replacement is rejected

- **WHEN** the decision Attestation changes after admission
- **THEN** ETHOS blocks before any effect
- **AND** later bindings derive from one immutable snapshot

#### Scenario: late coordination or competing decision blocks zero-effect

- **WHEN** a Lease, accepted head, decision, path, or reservation changes before
  the fence is acquired
- **THEN** ETHOS performs no Git or worktree effect

#### Scenario: worktree-remove failure is re-observed

- **WHEN** worktree removal fails
- **THEN** ETHOS re-reads ref, registration, and path
- **AND** reports the exact partial state rather than rollback success

#### Scenario: zero-effect retry is rebound after accepted history advances

- **WHEN** no effect occurred and accepted history advanced by ancestry only
- **THEN** fresh admission may replace the exact old fence and reservation
- **AND** divergence or any other drift blocks

#### Scenario: target-ref inspection is three state

- **WHEN** a target ref is present, absent, or unreadable
- **THEN** only explicit absence satisfies the postcondition

#### Scenario: destructive partial transition remains visible and recoverable

- **WHEN** any destructive boundary becomes partial or uncertain
- **THEN** inventory retains exact phase, target, decision, and recovery facts

#### Scenario: receipt-present cleanup retry converges

- **WHEN** the completion Attestation is durable but cleanup is incomplete
- **THEN** retry verifies it and performs only idempotent cleanup
- **AND** never recreates effect authority

#### Scenario: closeout-fence inspection is three state

- **WHEN** the exact fence is present, absent, or unverifiable
- **THEN** each recovery phase accepts only its explicitly declared state
- **AND** unverifiable state blocks

#### Scenario: successful cleanup preserves ordering

- **WHEN** cleanup follows durable completion
- **THEN** ETHOS releases the exact fence before removing the reservation

#### Scenario: effect-complete recovery precedes ordinary observation

- **WHEN** effect completion lacks its final Attestation
- **THEN** recovery resolves completion before ordinary lane observation

#### Scenario: dangling path and post-CAS exception fail closed

- **WHEN** a dangling path or post-CAS exception is observed
- **THEN** ETHOS treats the path as present and reports transition unknown

#### Scenario: native ownerless authority binding is exact

- **WHEN** any required decision or coordination field is absent or invalid
- **THEN** ETHOS rejects admission without inferring compatibility

#### Scenario: canonical and legacy reservations disagree

- **WHEN** historical reservation bytes coexist with the current carrier
- **THEN** current readers ignore historical bytes as authority
- **AND** no scan-order choice or compatibility merge occurs

#### Scenario: receipt compatibility is one way

- **WHEN** historical completion bytes are encountered after cutover
- **THEN** they remain inert history and cannot satisfy current recovery
- **AND** new completion uses Attestation v2 only

#### Scenario: damaged fence payload preserves independent lease truth

- **WHEN** a fence payload is invalid but Lease state is independently readable
- **THEN** inventory reports both facts separately
- **AND** invalid fence state cannot erase or authorize the Lease

### Requirement: Historical Work Lane semantic convergence

ETHOS SHALL preserve useful intent and unique semantics from a historical Work
Lane without requiring its obsolete implementation or Git ancestry to enter the
current terminal tree. Historical carriers remain immutable observations, not
mutation authority.

#### Scenario: Semantic refresh conflict fails closed

- **WHEN** the official candidate-base refresh encounters a semantic conflict
- **THEN** ETHOS MUST abort the replay and report `refresh_base_failed`
- **AND** it MUST restore the Work Lane branch and worktree to the expected clean
  head
- **AND** no manual rebase continue, skip, raw ref movement, or history
  replacement may be used to bypass the failure.

#### Scenario: Historical work is classified before implementation transfer

- **WHEN** a historical Work Lane is evaluated against current accepted truth
- **THEN** each useful obligation is classified as currently proved, uniquely
  valuable, superseded by stronger semantics, or obsolete
- **AND** only uniquely valuable semantics remain to be absorbed.

#### Scenario: Semantics are absorbed without replaying obsolete code

- **WHEN** current source and tests implement the historical lane's useful
  semantics exactly or more strongly
- **THEN** ETHOS records that semantic basis and permits exact retirement without
  rebasing or merging the historical implementation
- **AND** tree inequality alone does not imply missing product behavior.

#### Scenario: Historical implementation remains the best terminal form

- **WHEN** evidence shows that the historical implementation itself remains the
  shortest correct terminal form
- **THEN** an owned atomic Change may transfer that implementation onto the
  current candidate and regenerate HEAD-bound proof
- **AND** Git ancestry is preserved only when it carries necessary semantic or
  audit value, not as a universal retirement prerequisite.

#### Scenario: Historical facts are corrected without archive mutation

- **WHEN** independent replay or review corrects a fact recorded by the
  historical carrier
- **THEN** the active continuation MUST record a superseding correction with its
  reproducible inputs and digest
- **AND** the archived Change, historical Chronicle, and historical proof
  receipt MUST NOT be rewritten.

### Requirement: terminal retirement receipt

A linked-lane retirement invoked from the target worktree SHALL observe postconditions from a surviving repository control root after deleting the target worktree. When Lease, ref, and worktree are absent, the command SHALL return a passing terminal receipt.

#### Scenario: linked lane is retired from its own worktree

- **WHEN** the public retirement command removes the target worktree, ref, and Lease
- **THEN** postconditions are observed from a surviving control root and the command emits a passing terminal receipt

### Requirement: durable runtime wheel provenance

An installed package-only runtime SHALL retain a content-addressed local wheel path whose bytes match the manifest wheel SHA256. Reinstallation and lane creation SHALL validate that path without requiring the source checkout or a deleted staging directory.

#### Scenario: a package-only runtime materializes its successor

- **WHEN** the original build staging directory is absent
- **THEN** runtime installation uses the durable content-addressed wheel with matching bytes

### Requirement: accepted proof without active Change

A clean accepted root with no active OpenSpec Change SHALL execute package-only
governance and full proof without requiring a synthetic Change status payload.
Active or completed Changes SHALL retain strict status and artifact validation.

#### Scenario: all Changes are archived

- **WHEN** the official OpenSpec list is empty on a clean accepted root
- **THEN** governance uses an empty optional status payload and full proof proceeds

#### Scenario: a Change is active

- **WHEN** the official OpenSpec list selects an active Change
- **THEN** missing or invalid status and artifact fields remain blocking gaps

### Requirement: Invocation and editor bindings have distinct remediation

ETHOS SHALL distinguish a missing invocation actor, a different holder, and a
missing editor-root binding so each condition has one accurate public recovery
step.

#### Scenario: Invocation actor is absent

- **WHEN** a mutation requires the current Lease holder and `ETHOS_ACTOR` is
  empty
- **THEN** ETHOS reports `invocation_actor_missing` with the expected holder
- **AND** it does not misreport a different-holder conflict.

#### Scenario: Valid Lease lacks editor-root input

- **WHEN** the current holder has a valid Lease but required editor-root input
  is absent
- **THEN** ETHOS reports `editor_root_missing`
- **AND** the remediation binds or supplies the current Work Lane editor root
- **AND** it does not recommend starting another lane.

### Requirement: Independent peer effects remain recoverable

ETHOS SHALL treat each declared peer as an independent transaction and SHALL
NOT claim cross-peer atomicity. A request SHALL bind each peer's exact expected
OID, desired local object OID, and target ref. If one peer succeeds before
another fails, the terminal Attestation SHALL identify applied, failed, and
pending peers. Replaying the same request SHALL preserve peers already equal to
the desired OID and continue safely without replaying, re-signing, merging, or
rewriting any product object.

#### Scenario: one peer rejects the push

- **WHEN** an earlier peer applies and a later peer rejects its exact-CAS update
- **THEN** the result SHALL be a partial effect with immutable evidence
- **AND** unchanged request replay SHALL converge without rewriting the applied peer

#### Scenario: a peer is already current

- **WHEN** a peer target already equals the request's desired object OID
- **THEN** that peer SHALL be recorded as already applied
- **AND** no push or object reconstruction SHALL occur for that peer

#### Scenario: a peer diverges

- **WHEN** a peer target equals neither the exact expected OID nor desired OID
- **THEN** the request SHALL fail before the first new effect
- **AND** ETHOS SHALL NOT merge, replay, re-sign, or infer equivalence from its tree

### Requirement: Publication semantics have one owner per layer

The peer collection SHALL be the sole topology owner. One typed full-ref target
resolver SHALL own ref kind and lifecycle role. One `TransitionPlan` compiler
SHALL bind local object facts, selected proof Attestation, exact peer targets,
and effects. One Git executor SHALL own live remote observation, exact CAS,
post-write verification, and partial-effect Attestation. Public CLI and Git
hooks SHALL consume these owners and SHALL NOT recreate branch parsing, proof
selection, peer reconciliation, or object identity policy.

#### Scenario: public command and hook inspect one target

- **WHEN** `ethos publish` and pre-push evaluate the same target ref and local object
- **THEN** they SHALL project the same ref kind, lifecycle role, proof authority, and required gaps
- **AND** a missing proof SHALL name one executable `ethos prove --execute --expect-head <oid> --json` continuation

#### Scenario: observation projections are not mutation authority

- **WHEN** remote-tracking refs or provider status are displayed
- **THEN** those readers MAY describe current observations
- **AND** they SHALL NOT authorize or alter an exact-CAS publication effect

#### Scenario: several peers use one provider

- **WHEN** peer IDs and Git remotes are unique but provider labels repeat
- **THEN** topology SHALL remain valid
- **AND** each peer SHALL be independently observed and admitted

#### Scenario: no remote peer is declared

- **WHEN** local verification and installation commands are valid and peers are empty
- **THEN** local publication readiness SHALL remain valid
- **AND** no remote observation or hosted claim SHALL be manufactured

### Requirement: Continuous intent preserves bounded Changes

Every accepted feedback occurrence SHALL be preserved in the Attestation set
and selected to a semantic owner or explicit absence, contradiction, or
model-gap disposition. New input SHALL NOT expand an active Change implicitly.
Topology convergence SHALL not create or preserve a second carrier for Change
lineage, predecessor/successor meaning, hypothesis, experiment,
requirement-coverage, or scope/granularity semantics. Existing authoritative
owners remain the only sources; a missing public derived view SHALL be recorded
as a separate model gap rather than fabricated by this Change.

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** exact-CAS set union preserves every occurrence
- **AND** selections may feed disjoint future official OpenSpec Changes

#### Scenario: A Change's scope or granularity is evaluated

- **WHEN** a proposed obligation is considered for an active Change
- **THEN** it is admitted only when its intent, implementation, proof, and
  closeout form one reviewable outcome
- **AND** unrelated intent becomes a separate official Change or a
  non-authorizing Attestation rather than expanding the active Change

#### Scenario: Lineage and experimental reasoning are audited

- **WHEN** topology convergence audits predecessors, successors, hypotheses,
  experiments, or requirement coverage
- **THEN** it identifies the existing source owner and whether a public derived
  view is actually available
- **AND** it does not create a mutable Change DAG, hypothesis registry,
  experiment ledger, successor back-link, or replacement carrier when that view
  is absent

### Requirement: Deployed adopter readers remain bounded

ETHOS SHALL inspect the exact deployed transition and terminal-v1 repository
carrier without making either a proof or mutation authority.

#### Scenario: Package-only readers execute

- **WHEN** an installed wheel reads the deployed adopter fixture
- **THEN** `status` and `plan` SHALL pass without traceback
- **AND** `plan` SHALL bind carrier bytes, deny authority, and emit no v2 plan
- **AND** any transition-row drift SHALL fail closed.

### Requirement: Candidate proof admission selects repository authority

ETHOS SHALL use one repository-transition proof query for readiness and mutation.
The query SHALL bind exact repository identity, HEAD, tree, proof policy, and the
applicable transient Commitment or verified archive effect. Candidate acceptance,
accepted publication, and control-replacement admission SHALL consume that query.

#### Scenario: Historical Work Lane proof is not applicable

- **WHEN** a proof is bound only to a retired Work Lane relation
- **THEN** it does not authorize a current repository transition
- **AND** it remains queryable as historical evidence

#### Scenario: Retired Work Lane leaves the only applicable proof

- **GIVEN** a verified archive effect and proof bind the exact repository, HEAD, tree, and current proof policy
- **WHEN** the active Change and former Work Lane no longer exist
- **THEN** repository transition selects that exact evidence without scanning an archived Commitment carrier
- **AND** no historical ownership is recreated

#### Scenario: Applicable proof conflict fails closed

- **WHEN** selected proof bindings disagree
- **THEN** ETHOS returns the first stable mismatch coordinate
- **AND** no repository effect is authorized

#### Scenario: Closeout readiness and apply share proof admission

- **WHEN** accepted-root closeout is evaluated without and with `--apply`
- **THEN** both evaluations query the same candidate HEAD and proof selector
- **AND** a proof-selection mismatch cannot appear only after apply is requested

#### Scenario: Wrong authority cannot satisfy candidate acceptance

- **WHEN** a proof names another repository, HEAD, tree, policy, or applicable authority
- **THEN** ETHOS rejects it with a specific mismatch coordinate
- **AND** does not infer authority from another proof on the same HEAD

### Requirement: Publication selects repository authority

ETHOS SHALL select the exact accepted-HEAD repository proof and bind its
repository identity, commit, tree, policy, and verdict.

#### Scenario: Historical or conflicting proof shares the HEAD

- **WHEN** several proofs share the accepted HEAD
- **THEN** only the exact applicable repository proof SHALL apply, or selection fails closed on conflict

### Requirement: Exact local Git object projection

A product commit or annotated release tag SHALL be created and signed once in
the local Git authority. ETHOS SHALL verify the selected local object's signature
and publish the exact existing object bytes. Transport authentication, provider
identity, and provider presentation SHALL remain separate observations.

#### Scenario: one signed commit reaches two peers

- **WHEN** one trusted local commit is published to two independent peers
- **THEN** both peer refs equal the local commit OID
- **AND** transport credentials do not enter product object identity

#### Scenario: one annotated tag reaches two peers

- **WHEN** one trusted local annotated tag is published to two independent peers
- **THEN** local and peer tag object OIDs, peeled commits, and trees are equal

#### Scenario: a new remote ref is created

- **WHEN** the target ref is absent
- **THEN** the plan binds Git's zero OID as the exact expected state

#### Scenario: tree-only equality is insufficient

- **WHEN** a peer object has the expected tree but a different object OID
- **THEN** publication parity fails closed
- **AND** ETHOS does not accept replay, re-signing, identity rewrite, or tree-only equivalence

#### Scenario: proof authority is exact

- **WHEN** publication selects a proof Attestation
- **THEN** the plan binds its exact ID, repository identity, commit, tree, gate-set policy digest, and verdict
- **AND** hook and receipt apply reject coordinate drift

### Requirement: Lifecycle effect finalization authorizes exact transition paths

ETHOS SHALL use one verified OpenSpec lifecycle-effect authority for official
archive, canonical-spec projection, and post-archive closeout.
The authority SHALL bind repository identity, the transient Commitment digest,
previous and resulting Git facts, exact changed paths, official OpenSpec result,
and terminal effect Attestation. Status, plan, prove, land, prewrite, and hooks
SHALL consume that same authority. A durable partial effect SHALL recover through
the same public operation by exact CAS.

#### Scenario: Exact archive transition is congruent across readers

- **WHEN** official OpenSpec archive completes and the Git effect Attestation binds the exact source and result
- **THEN** status, plan, prove, land, prewrite, and hooks attribute the finalization paths identically
- **AND** no reader requires a new active Change or archived Commitment carrier

#### Scenario: A committed archive is recovered after controller loss

- **WHEN** the exact archive Git effect is durable but its rebuildable projection is incomplete
- **THEN** retry recognizes the effect Attestation and completes projection forward
- **AND** it does not replay OpenSpec, reverse the ref, or create another product commit

#### Scenario: Missing or tampered archive authority fails closed

- **WHEN** the official result, exact Git facts, effect Attestation, or changed path set is missing, ambiguous, stale, or tampered
- **THEN** ETHOS reports the first exact missing coordinate and one public next command
- **AND** it does not infer authority from an archive path or historical lane

#### Scenario: Finalization state is classified before mutation

- **WHEN** finalization observes a missing, expired, foreign, or valid Lease
- **THEN** it reports that exact coordination state and its one public action
- **AND** it never assumes holder identity or edits SQLite directly

#### Scenario: Zero-effect failure has no compensation gap

- **WHEN** preflight fails before an effect
- **THEN** the receipt preserves the original failure and proves owned assets absent
- **AND** it reports no compensation failure for an effect that never occurred

#### Scenario: Hook observation cannot re-enter Git maintenance

- **WHEN** a reference transaction invokes admission while Git holds a ref lock
- **THEN** the hook performs only bounded read-only observations
- **AND** unavailable observation fails closed without re-entering maintenance

### Requirement: Hook runtime currentness is mutation admission
ETHOS SHALL distinguish runtime byte integrity from accepted-source currentness.
A hook runtime SHALL authorize repository mutation only when it is the single
Git-common-dir selected runtime, its manifest is valid, and its source commit
and tree equal the exact expected ETHOS identity.

#### Scenario: intact runtime was built from older accepted source
- **WHEN** every recorded runtime byte is intact but its source commit or tree differs from the expected accepted identity
- **THEN** runtime observation reports a stable stale-source required gap
- **AND** prewrite, hook, ref effect, and lifecycle mutation paths fail closed

#### Scenario: accepted runtime is current
- **WHEN** the selected runtime bytes, launchers, source commit, and source tree all match their expected identities
- **THEN** the existing hook runtime binding reports no required gap
- **AND** hooks, diagnosis, repair, and package-only commands resolve that same selected immutable runtime.

#### Scenario: repair replaces the stale projection
- **WHEN** the exact public repair command succeeds
- **THEN** the command validates the candidate runtime and complete hook bundle before atomically selecting it
- **AND** post-observation proves selection, byte integrity, source currentness, and launcher binding before reporting success.

#### Scenario: proof is missing at hook admission
- **WHEN** a hook denies an exact HEAD because its required proof is absent
- **THEN** the report contains one executable command bound to the selected runtime, repository root, and exact HEAD
- **AND** the command does not depend on ambient `PATH` command discovery.

### Requirement: Git-common hook runtime activation is singular

ETHOS SHALL maintain one effective hook generation and one selected immutable
runtime per Git common directory. The invoking repository authority SHALL
validate a candidate runtime and hook bundle before atomically replacing the
runtime selector and common hook activation. Linked worktrees SHALL consume
that common selection without interpreting historical launchers or profiles as
another runtime authority.

#### Scenario: One install converges all linked worktrees

- **GIVEN** linked worktrees resolve different generated hook generations
- **WHEN** the public hook installation command succeeds
- **THEN** repository-common Git config owns the effective `core.hooksPath`
- **AND** the Git-common runtime selector identifies the one runtime used by every installed hook and package-only remediation command
- **AND** owned worktree-local activation overrides are absent.

#### Scenario: Cleanup preserves every observed consumer

- **WHEN** hook/runtime cleanup evaluates generated generations
- **THEN** it retains the selected runtime and every generation named by effective config, live process commands, or in-flight operation records
- **AND** it removes only other generated runtimes and hook generations
- **AND** an unreadable consumer source blocks deletion.

#### Scenario: Historical linked checkout cannot veto current activation

- **GIVEN** the invoking repository resolves a valid accepted runtime source identity
- **AND** a linked historical checkout contains an obsolete or invalid profile
- **WHEN** the public hook installation command runs from the invoking repository
- **THEN** every linked worktree validates the same common activation and selected runtime against the invoking repository's exact source identity
- **AND** the historical profile does not select or veto that identity
- **AND** unreadable Git configuration, selector, or runtime projection still fails closed.

#### Scenario: activation validation fails

- **WHEN** the candidate runtime, manifest, entrypoint, or generated hook bundle fails validation
- **THEN** neither the runtime selector nor effective common hook activation changes
- **AND** the previously selected valid runtime remains the sole selected runtime.

### Requirement: Python test basetemp has one explicit owner

An ETHOS Python gate SHALL distinguish owned from caller-supplied temporary paths.

#### Scenario: Internally allocated Python test basetemp is reclaimed

- **WHEN** the Python test gate allocates its default pytest basetemp
- **THEN** the gate records that it owns the path
- **AND** it removes that exact path after successful or failed execution
- **AND** cleanup failure remains visible.

#### Scenario: Caller-managed Python test basetemp is preserved

- **WHEN** `ETHOS_TEST_BASETEMP` supplies the pytest basetemp
- **THEN** the gate records that the path is externally managed
- **AND** it never recursively removes that path.

### Requirement: Official spec-free Changes compile acceptance

ETHOS SHALL compile deterministic non-empty acceptance for a completed official
OpenSpec Change that explicitly declares `skip_specs: true` and contains no
requirement deltas. The acceptance SHALL use only official OpenSpec projection
facts and SHALL NOT require fake requirements, `commitment.toml`, or another
tracked intent carrier.

#### Scenario: Completed spec-free Change is selected

- **GIVEN** the official OpenSpec projection declares `skip_specs: true`
- **AND** its required proposal, design, and tasks artifacts are complete
- **AND** it contains no requirement deltas
- **WHEN** ETHOS compiles the selected Change
- **THEN** it produces one deterministic non-empty transient Commitment
- **AND** the Commitment remains applicable through the attested official archive transition

#### Scenario: Empty deltas are not implicitly accepted

- **WHEN** a Change has no requirement deltas but lacks the official spec-free declaration or completed artifacts
- **THEN** ETHOS fails closed with the exact OpenSpec acceptance gap
- **AND** no filename pattern, product category, compatibility carrier, or archived directory grants authority

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid current Lease SHALL be able to create and
complete exactly one official OpenSpec Change before its transient Commitment
exists. Bootstrap authority SHALL derive only from the official active Change
identifier and artifact graph, and SHALL cover only artifact paths under that
exact Change root.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design, tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier is admitted

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path attribution
- **AND** bootstrap authority grants no additional scope or durable permission

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** zero or several active Change identifiers are observed, an identifier is invalid, or a requested path is outside the official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does not authorize the write

### Requirement: Remote publication observations preserve epistemic state

The existing remote-publication effect adapter SHALL be the sole owner of
bounded live remote-ref observation for exact publication. It SHALL preserve
whether a target ref is present, absent, or unavailable. Public CLI and Git
hooks SHALL consume that observation and SHALL NOT recreate availability,
ancestry, or object-identity judgments from missing coordinates.

#### Scenario: exact publication uses the target observer

- **WHEN** `ethos publish --ref <full-ref> --probe-remote` evaluates declared peers
- **THEN** the remote-effect adapter SHALL perform one bounded observation for
  each exact peer/ref target
- **AND** remote-tracking state or general reachability SHALL NOT substitute for
  that exact ref fact.

#### Scenario: a required remote fact is unavailable

- **WHEN** an exact target observation times out, cannot start, or exits without
  a valid ref result
- **THEN** publication SHALL return verdict `unknown` with the exact peer/ref
  missing fact, command boundary, cwd, exit or timeout state, and stderr
- **AND** it SHALL NOT report the ref as absent, divergent, or non-fast-forward.

#### Scenario: a divergent remote ref is observed

- **WHEN** a successful observation returns an existing OID that is neither the
  desired OID nor an admitted fast-forward predecessor
- **THEN** publication SHALL return verdict `block` with the observed OID and
  target-drift reason
- **AND** no remote mutation SHALL occur.

#### Scenario: apply re-observes the exact request

- **WHEN** a valid publication request is applied
- **THEN** every target SHALL be re-observed through the same bounded observer
  before the first effect and after its peer-local exact CAS
- **AND** unavailable post-observation SHALL not be reported as successful
  publication.
