# ETHOS Repository Governance

## Purpose

ETHOS SHALL govern repository operation lifecycles: status, plan, prove, land,
publish, quality, evidence, release readiness, and evolution.

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

- **WHEN** ETHOS emits `status`, `prove`, `land`, or `publish` JSON for any
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
- **THEN** it checks declared subjects, purposes, authority and reachable
  relationships without requiring evidence or lifecycle directories
- **AND** product roots remain only for distinct subject responsibilities
- **AND** retained evidence follows its producer, consumer, binding and lifetime
- **AND** no ETHOS extension root is mandatory for an adopter

#### Scenario: First-run guidance is placed by function

- **WHEN** ETHOS has one first-run onboarding document
- **THEN** it SHALL live under the `guides` function root as `docs/guides/quickstart.md`
- **AND** links, stable-path metadata, taxonomy metadata, registry output, and
  command examples SHALL resolve to that path
- **AND** the former onboarding root SHALL not remain as a historical habit or
  redirect root

#### Scenario: A documentation directory needs a README

- **WHEN** a documentation directory is evaluated for a README
- **THEN** two or more immediate navigable children SHALL have a README
  with a local route into the directory's content
- **AND** a directory with one substantive document SHALL not receive a
  placeholder README merely because the directory exists
- **AND** an empty directory or `.gitkeep` SHALL be removed

#### Scenario: Documentation taxonomy is projected

- **WHEN** the Docs Registry reads the ETHOS documentation tree
- **THEN** role, state, subject, and relation metadata are validated by the
  registry owner and directory names express subject/function rather than
  lifecycle state
- **AND** the registry SHALL report missing or invalid metadata, duplicate
  subjects, unindexed plans, and invalid README dispositions
- **AND** the `markdown-links` gate SHALL report broken links

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and does
  not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order,
  contracts, evidence, claims, and proof rather than by directory name
- **AND** proposed behavior and acceptance belong in the selected official
  Change; plans, research and revisit conditions supply linked context only
- **AND** no generic intent directory becomes a second change authority

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, guides, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

#### Scenario: Declared normative documentation has a reader route

- **WHEN** the repository declares normative sources inside its configured documentation root
- **THEN** each declared source is reachable from that root's registered README through actual local Markdown links
- **AND** reference links and intermediate directory READMEs remain valid routes, cycles terminate, and fenced examples do not become navigation
- **AND** missing routes are reported without absorbing sources outside the documentation root or changing source bytes

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

One owner SHALL compile commit policy for subject, signature and optional
author/committer constraints from the paradigm contract and the tracked
`[commit_policy]` declaration; every introduced commit carries an SSH signature.
Identity, cryptographic trust, transport and Forge attribution SHALL remain
distinct. Admission SHALL apply trusted prestate policy; a candidate SHALL NOT
waive its own integration obligations.

#### Scenario: Real signature verification

- **WHEN** admission evaluates an introduced commit
- **THEN** admission verifies exact object bytes against the protected trust anchor
- **AND** a signature envelope with invalid cryptography is rejected

#### Scenario: Verification inputs remain current

- **WHEN** one or many exact objects are verified against native SSH trust
- **THEN** every object uses the same captured configuration, anchor and revocation material
- **AND** source trust changes before observation completes reject the result
- **AND** temporary verification material is removed on normal exit or reported failure

#### Scenario: Identity requirements are declared

- **WHEN** policy constrains author or committer identity
- **THEN** the same constraint is checked before commit and on integrated objects
- **AND** absent constraints add no generic-adopter identity restriction

#### Scenario: Candidate weakens signing policy

- **WHEN** a candidate declares `signing_required = false` or another signing format
- **THEN** compilation ignores the restated field
- **AND** its introduced range still requires a trusted SSH signature on every commit

#### Scenario: Malformed policy fails closed

- **WHEN** a present identity constraint has malformed or unknown fields
- **THEN** compilation returns a precise error rather than disabling admission

#### Scenario: Independent evidence planes

- **WHEN** CI verifies an existing commit
- **THEN** it invokes the common owner without inventing authors or signing keys
- **AND** local signature success does not claim Forge verification

#### Scenario: Current commit policy is audited

- **WHEN** repository audit or head-bound proof evaluates current commit policy
- **THEN** it reports the compiled declaration, local identity, subject, and
  signature facts through the same compiler used by mutation
- **AND** it does not infer tracked policy from mutable Git configuration or
  GitLab verification from local Git output.

#### Scenario: Identity allowlist fields have no policy meaning

- **WHEN** a present commit-policy table contains `identity_mode` or
  `allowed_identities`
- **THEN** compilation fails closed with the exact unknown fields
- **AND** ETHOS does not preserve them as permissions, trust anchors, or
  compatibility metadata.

#### Scenario: CI verifies but does not manufacture commit identity

- **WHEN** a native CI projection prepares Git for repository checks
- **THEN** it does not synthesize an author identity, signing key, or
  `commit.gpgsign` setting when the job creates no commit
- **AND** it verifies existing objects through the repository-owned gates
  without an embedded TOML parser or policy default.

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

#### Scenario: Empty current scope does not rehydrate historic archive authority

- **GIVEN** proof resolution has no current changed paths and retains only a
  valid historic OpenSpec archive authority
- **WHEN** full proof compiles its TransitionPlan for the current HEAD
- **THEN** the plan does not carry that historic archive authority as a prior
  attestation
- **AND** the plan does not report `proof_archive_scope_stale` solely because
  historic authorized paths are absent from the empty current scope
- **AND** an applicable non-empty current scope retains strict archive-path
  validation.

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
- **AND** the next action is
  `ethos prove --full --execute --expect-head <HEAD> --json`

#### Scenario: Work Lane land dry-run with executed proof is ready

- **GIVEN** a clean Work Lane with no structural landing gaps
- **AND** a valid executed proof record exists for the Work Lane HEAD
- **WHEN** `ethos land --json` evaluates the Work Lane
- **THEN** ETHOS reports `ready_to_land`

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
compiled from each selected official Change snapshot. Official proposal, specs, design,
tasks, metadata, configuration, and exact repairs named by current structured
official validation failures are the sole tracked intent and lifecycle
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

#### Scenario: Official validation requires a canonical spec repair

- **GIVEN** official strict validation reports
  `openspec_validation_failed:spec:<capability>`
- **AND** that failure blocks ordinary material-scope resolution
- **WHEN** the current Work Lane requests prewrite for exactly
  `openspec/specs/<capability>/spec.md`
- **THEN** ETHOS admits that exact repair path under the selected active Change
  or its verified archived source
- **AND** unrelated canonical specifications and all non-specification paths
  remain blocked
- **AND** malformed or ambiguous capability identifiers grant no authority

#### Scenario: Official validation requires an active Change artifact repair

- **GIVEN** one selected active Change has a complete official artifact graph
- **AND** current strict validation marks that exact Change invalid and reports
  a structured `ERROR` or `WARNING` issue path
- **AND** that issue path resolves uniquely against the Change root or its
  `specs/` root to one existing output in the official artifact graph
- **AND** the official output retains its lexical path beneath the repository
  root and that exact path is a non-symlink regular file
- **WHEN** the owning Work Lane requests prewrite for exactly that output
- **THEN** ETHOS admits only that exact repair path without first requiring a
  valid Commitment
- **AND** malformed, absolute, traversing, missing, ambiguous,
  unrelated-Change, symlinked, non-regular, directory-wide, and mixed paths
  remain blocked
- **AND** an `INFO` issue grants no repair authority
- **AND** the repair authority disappears when fresh strict validation no longer
  reports the matching issue.

#### Scenario: Official archive leaves a canonical validation failure

- **GIVEN** no active Change remains and exact completed archive evidence
  identifies the selected Change and its canonical specification output
- **AND** current official strict validation reports a blocking structured
  issue for that canonical specification
- **WHEN** the currently coordinated Work Lane requests that exact repair path
- **THEN** prewrite and host admission permit only the validator-named repair
- **AND** current runtime, actor, Lease and supplied postimage checks still apply
- **AND** missing or mismatched archive evidence, unrelated validation failures
  and additional requested paths do not acquire repair permission
- **AND** the repaired source requires fresh strict validation and proof without
  recreating the active Change or repeating its completed archive effect

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
- **THEN** the result SHALL report read files, the exact plan for the ETHOS
  profile and the official OpenSpec configuration, apply criteria, conflicts,
  and rollback instructions
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
- **AND** it resolves the named Work Lane ref as `binding_head` for the request's
  independent fresh Git-coordinate comparison
- **AND** ordinary writes bind the mutation request to current `HEAD` while the
  Lease remains the four-field lane-holder generation
- **AND** missing named refs, mismatched Git heads, accepted, candidate,
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
- **THEN** it returns `pass`, `block`, or `unknown` with `why`, `next_action`,
  and `required_gaps`
- **AND** the decision binds action, resource, expected mutable state, policy
  refs, evidence refs, and decision basis
- **AND** a `pass` applies only to that request and mints no role, capability,
  session, token, or reusable authorization.

#### Scenario: confirmation and user instruction do not bypass policy

- **WHEN** a caller supplies `--apply`, `--authorize`, another destructive
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
  outside the candidate tree and a bootstrap decision Attestation.

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
plans. A clean linked Work Lane whose exact HEAD equals or is an ancestor of the
current accepted HEAD SHALL be eligible for deletion-only landed retirement
without reconstructing historical proof, Commitment, or Lease authority.
Exceptional interpretive judgment SHALL remain an exact, non-authorizing
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing when a live Lease exists and
  postcondition Attestations for the applied effects
- **AND** no tracked decision record is required

#### Scenario: clean linked accepted residue retires without historical proof

- **WHEN** a named linked `work/*` Lane is clean and its exact HEAD equals or is
  an ancestor of the freshly observed accepted HEAD
- **AND** its ref, worktree binding, accepted ref, actor, and requested HEAD are
  unchanged at effect time
- **THEN** `ethos lane retire landed` SHALL remove only that exact worktree and
  branch through the existing exact-CAS effect owner
- **AND** it SHALL compile the deletion as a repository effect with no
  Commitment or proof-Attestation prerequisite
- **AND** it SHALL emit exact effect and postcondition evidence

#### Scenario: live Lease retains holder authority

- **WHEN** an otherwise retireable linked Lane has a valid Lease
- **THEN** only the exact current holder MAY apply landed retirement
- **AND** the Lease generation SHALL be re-observed and revoked exactly in the
  same bounded transition

#### Scenario: absent or expired Lease does not resurrect history

- **WHEN** an otherwise retireable linked Lane has no Lease or only an expired
  exact Lease row
- **AND** the invocation names a non-empty actor and explicitly authorizes the
  deletion-only transition
- **THEN** ETHOS SHALL respectively require the Lease to remain absent or revoke
  the exact expired row before committing retirement
- **AND** it SHALL NOT require Lease reacquisition, holder impersonation,
  historical proof, or a compatibility carrier

#### Scenario: unsafe retirement remains blocked

- **WHEN** the selected Lane is dirty, its HEAD is not accepted ancestry, its
  Lease state is unknown, a valid Lease belongs to another holder, or any exact
  Git, worktree, Lease, actor, or accepted coordinate drifts
- **THEN** retirement SHALL fail closed without deleting the branch or worktree
- **AND** no inventory entry, stale receipt, self-supplied holder, or historical
  relation SHALL substitute for the missing fact

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
- **THEN** the payload includes a read-only availability observation for each
  declared peer under `remote_observations`
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

### Requirement: Generated Evidence Boundary

Generated proof artifacts SHALL remain outside repository truth, with
deterministic latest-artifact writes. Product and contributor package builds
SHALL build in a disposable staging directory and replace
`build/artifacts/python`, or `build/artifacts/release/python` for a release
build, with exactly one admitted wheel; they SHALL rely on the repository-level
ignore and SHALL NOT use root `dist/` or add an output-local `.gitignore`.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.

#### Scenario: An interrupted coverage writer does not block future proof forever

- **GIVEN** a coverage writer exited or died while holding the native file lock
- **WHEN** a later Python owner test gate starts for that same evidence home
- **THEN** the operating system has released that lock and the gate acquires the
  writer boundary
- **AND** it never preempts a live holder
- **AND** a lock held past the configured bounded wait
  (`ETHOS_COVERAGE_LOCK_WAIT_SECONDS`) fails with the lock path rather than
  waiting indefinitely
- **AND** the lock file remains ignored generated state, not repository truth.

#### Scenario: Package build writes to the semantic artifact home

- **WHEN** the product full proof executes its package build gate or a
  contributor follows the documented package-build command
- **THEN** the `build` owner runs `uv build` with `--out-dir <staging>` and
  `--no-create-gitignore`, then replaces `build/artifacts/python` with the one
  admitted wheel
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

The repository SHALL explicitly declare zero or more peers with unique IDs and
Git remotes. Repeatable provider labels SHALL select only transport/observation
adapters, never a primary, product identity, object producer, signing authority
or inter-peer dependency. Existing local Git objects SHALL be the sole source.
Each optional peer SHALL be independently observed, updated, verified, retried
and attested.

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

One provider-neutral resolver SHALL map full ref to kind, lifecycle role, local
object and allowed effect. Only accepted, release and proposal branches or
policy-matching annotated release tags are publishable; tags have release-
publication role, not `other`. Candidate/work refs stay local. Unknown refs,
lightweight tags, undeclared remotes, ambiguous topology, untrusted signatures
and non-admitted roles SHALL fail before remote writes.

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

- **WHEN** a tool is named by a catalog or planned-presence record
- **THEN** that record SHALL NOT make it an active quality gate
- **AND** activation SHALL require a gate in `system/gates.toml` plus its native
  configuration or supply owner
- **AND** the catalog SHALL be deleted rather than retained as parallel state

#### Scenario: Tool admission is positively owned

- **WHEN** a tool participates in a current quality obligation
- **THEN** its active gate SHALL be declared in `system/gates.toml`
- **AND** its native configuration or supply policy SHALL own tool-specific
  behavior and version identity
- **AND** no second tool catalog or planned-presence record SHALL become an
  active quality floor

#### Scenario: Optional method packs remain replaceable

- **WHEN** an agent uses Superpowers or another method pack to plan or review a
  change
- **THEN** the method pack MAY be recorded as execution context
- **AND** repository truth SHALL still require promoted source, docs, OpenSpec,
  claim, evidence, or command proof
- **AND** missing method-pack availability SHALL NOT block ETHOS repository
  governance when equivalent evidence discipline is satisfied

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL return a runner bootstrap for a newly started Work Lane that uses
the repository-selected immutable Git-common package runtime. The bootstrap
SHALL remain source-independent and SHALL NOT assume that the adopter checkout
or its project lock exposes an `ethos` executable.

#### Scenario: An adopter Work Lane uses its selected package runtime

- **GIVEN** the repository has a valid selected immutable runtime
- **WHEN** `ethos lane start` returns the Work Lane bootstrap
- **THEN** the command invokes that runtime's Python with `-B -I -m ethos.cli`
- **AND** it targets the new Work Lane root explicitly
- **AND** it does not create a checkout `.venv` or execute `uv run ... ethos`.

#### Scenario: a Work Lane uses its bootstrap runner

- **WHEN** the operator runs the returned runner from the linked Work Lane
- **THEN** the selected package-only runtime executes against that exact
  Work Lane root
- **AND** no checkout-local environment or adopter dependency lock is required
  to provide the ETHOS entrypoint.

#### Scenario: No selected runtime is available

- **WHEN** ETHOS cannot resolve a valid selected immutable runtime before
  starting the lane
- **THEN** lane creation fails closed before creating the ref, Lease, or
  worktree
- **AND** the result reports the exact runtime-selection gap.

### Requirement: Deterministic Official OpenSpec Tool Supply

ETHOS SHALL invoke the repository-locked official `@fission-ai/openspec`
package from its declared local runtime and CI bootstrap. The effective package
identity SHALL derive from the repository package declaration and lockfile;
ambient npx, PATH, cache, and global versions SHALL not be accepted as a
fallback. Adoption SHALL NOT generate provider CI surfaces or OpenSpec artifacts
beyond the official default configuration.

#### Scenario: ETHOS-owned fallback and CI supply are inspected

- **WHEN** a maintainer inspects the OpenSpec adapter and CI bootstrap
- **THEN** each repository-owned package invocation SHALL resolve the locked
  `@fission-ai/openspec` identity
- **AND** strict official OpenSpec validation SHALL remain the governance gate
- **AND** adoption SHALL plan no CI carrier and no OpenSpec carrier beyond the
  official default configuration.

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
- **THEN** each packaged declaration is read from its sdist-local canonical
  source named by the native package declaration
- **AND** the wheel contains byte-identical inputs under
  `ethos/resources/<canonical-source-relative-path>` without renamed source hierarchy
- **AND** package-owned guidance and build identity use the same resource namespace
- **AND** the build does not require the original checkout or adopter-owned inputs.

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
  worktree binding, dirty state, four-field Lease observation, decision
  Attestation, intended disposition, and target-observation evidence for each
  lane
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

### Requirement: Refresh-base replay is signing-bound and compare-and-swap safe

ETHOS SHALL replay the admitted Work Lane SHA onto the admitted candidate SHA
through native Git rebase using the compiled commit policy and the paradigm's
SSH signature. It SHALL revalidate both admitted SHA snapshots immediately
before replay, validate every new replayed subject and signature before any
Git-common effect, and compare-and-swap the Work Lane ref from its admitted old
SHA before attaching it again.

#### Scenario: Ambient Git configuration attempts to disable tracked signing

- **GIVEN** a governed repository
- **AND** ambient or local Git configuration disables `commit.gpgsign`
- **WHEN** `ethos lane refresh-base --apply` replays one or more commits
- **THEN** every new replayed object is still SSH-signed
- **AND** every object passes the configured trust verifier before the Work Lane
  ref or Lease changes.

#### Scenario: unavailable signing transport blocks before replay

- **GIVEN** the repository's configured signer cannot create a replayed object
  non-interactively
- **WHEN** native rebase attempts to create its first replayed object
- **THEN** ETHOS reports the captured Git failure instead of a speculative
  signer-probe result
- **AND** it aborts replay and restores the original branch, HEAD, index,
  worktree, ref, and Lease.

#### Scenario: A replayed subject or signature is invalid

- **GIVEN** native rebase produced a candidate-descended detached HEAD
- **WHEN** any commit in the exact candidate-to-rebased range violates the
  compiled subject policy or fails signature trust
- **THEN** ETHOS reports the first exact policy or trust gap
- **AND** it restores the pre-refresh state before any Git-common effect.

#### Scenario: admitted snapshots move during preflight

- **GIVEN** a refresh captured Work Lane and candidate SHA values
- **WHEN** either value changes before replay, or the Work Lane ref changes
  before compare-and-swap
- **THEN** ETHOS reports the corresponding `refresh_base_snapshot_stale` gap
- **AND** it does not overwrite the newer ref or retain a replayed checkout.

#### Scenario: Work Lane moves before replay compare-and-swap

- **GIVEN** detached replay produced and validated a candidate-descended HEAD
- **WHEN** the Work Lane ref no longer equals its admitted old SHA before
  compare-and-swap
- **THEN** ETHOS reports `refresh_base_snapshot_stale:work_lane`
- **AND** it reattaches to the newer branch state without overwriting that ref.

### Requirement: Committed Adopter Profile Policy At Closeout

ETHOS SHALL resolve adopter proof policy from the promoted committed tree when
accepted-root closeout evaluates an exact candidate advance before the accepted
worktree has reset to that candidate commit. The implementation of this policy
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
supersession, or retirement, its TransitionPlan SHALL bind branch and HEAD,
accepted relation, the four-field Lease observation when present, decision
Attestation, dirty provenance, disposition, recovery, and evidence. Replay also
binds implementation, focused regression, owned proof, and accepted absorption.
Any target drift invalidates the decision.

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
  accepted HEAD and relation, exact four-field Lease observation when present,
  exact target observation, selected decision Attestation, completion state,
  and recovery package integrity, ETHOS treats the exceptional effect as
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
reference before an irreversible closeout action. The preservation outcome
SHALL record Git status provenance, exact target head, recoverable content
manifest or patch digest, semantic comparison result, and the resulting
disposition. A clean accepted-absorption finding alone SHALL NOT discard an
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

ETHOS SHALL retain safe repository-relative normative source declarations as
intent metadata independently from directory roots. Current proof SHALL be
selected by its Attestation predicate and exact bindings, independently from
documentation locations or historical evidence directories.

#### Scenario: Root-level normative source is declared

- **WHEN** an adopter declares `normative_sources = ["guidelines.md"]`
- **THEN** the typed current binding retains that exact safe source declaration
- **AND** directory roots keep their path-safety contract without creating a
  second evidence-root candidate selector.

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

ETHOS SHALL own one typed profile binding and compose official OpenSpec
configuration initialization and readiness. Optional domain, documentation,
Skills and provider surfaces SHALL retain their own owners.

#### Scenario: A repository is adopted

- **WHEN** authorized exact-HEAD adoption targets an eligible Git repository
- **THEN** it plans the ETHOS profile and the selected native OpenSpec configuration
- **AND** no placeholder, generic project context, artifact rules or unrelated surface is invented

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles its default profile binding
- **THEN** one strict frozen declaration validates the in-memory value and native TOML serialization
- **AND** no profile registry, renderer manifest, digest snapshot or template environment becomes a second owner

#### Scenario: Existing bootstrap content differs

- **WHEN** an ETHOS binding is invalid, symlinked, non-regular or unreadable
- **THEN** adoption refuses the exact path without an implicit merge, alias or migration
- **AND** a valid existing profile is preserved, while an empty ETHOS profile may be replaced
- **AND** an empty native OpenSpec configuration remains an invalid existing carrier rather than absent configuration

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has not selected optional documentation, Skills, schemas, generated assets or hosted providers
- **THEN** their absence does not become a bootstrap gap
- **AND** native configuration and applicable material-scope correctness remain independently enforced

#### Scenario: Configuration is absent

- **WHEN** adoption initializes native configuration
- **THEN** its bytes match the official initializer's default configuration
- **AND** a first Change is usable through the official CLI without generated directory anchors

#### Scenario: Native meaning cannot be preserved

- **WHEN** configuration fields, schema resolution, rule applicability or required templates fail native validation
- **THEN** adoption blocks before writing and retains native warnings and reasons
- **AND** unavailable supply or observation remains UNKNOWN rather than malformed-user-content blame
- **AND** a pointer-only external store receives an explicit unsupported-operation reason, independent of host registration

#### Scenario: Authored configuration and custom schemas already exist

- **WHEN** the official reader selects valid YAML or YML and resolves repository-owned schema inputs
- **THEN** their exact bytes remain unchanged
- **AND** an explicit expected-plan digest rejects changed configuration, schemas or templates before apply

#### Scenario: A file effect fails

- **WHEN** an admitted write or its native postcondition fails
- **THEN** every independently safe owned write is compensated without overwriting intervening content
- **AND** incomplete or unobserved recovery is not reported as successful adoption
- **AND** the initiating failure and each failed compensation remain observable
- **AND** no multi-file crash-atomic guarantee is inferred from individual atomic replacements

### Requirement: Current product revision one-binding external-adopter observation is bounded and durable

ETHOS SHALL distinguish its sole binding from native initialization effects when
observing isolated adopter clones. Evidence SHALL bind exact inputs and effects
without private adopter coupling or claims beyond the exercised boundary.

#### Scenario: Missing binding is created without unrelated writes

- **WHEN** an isolated clone lacks the ETHOS profile
- **THEN** preview reports that binding and any required native configuration initialization separately
- **AND** authorized exact-HEAD apply preserves the source clone and unrelated files

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** an existing binding conflicts or its native configuration is invalid
- **THEN** no implicit merge, alias or replacement hides the conflict
- **AND** the result preserves the precise owning reason

#### Scenario: Current observation is promoted without private coupling

- **WHEN** an observation is retained as product evidence
- **THEN** it binds revisions, observed outcomes and the raw-bundle identity without host paths or credentials
- **AND** native backend parity, full semantic correctness, hosted execution and independent review require their own evidence

### Requirement: Linked Work Lane retirement has one exact effect

Landed and superseded retirement SHALL share one strict request and owner,
binding actor, mode, lane ref/HEAD, clean linked path and accepted ref/HEAD.
Consumed Leases SHALL bind only lane ref, holder, generation and expiry under
SQLite transaction; Git facts remain independent. Remove only the selected clean
checkout and compare-delete its exact ref in a transaction verifying accepted.

#### Scenario: Landed preview supplies an executable exact continuation

- **WHEN** an admitted preview selects one landed branch without an expected HEAD
- **THEN** its next command binds that branch's observed HEAD, not accepted's HEAD
- **AND** executing it rechecks all current admission and exact-effect conditions
- **AND** an explicitly supplied expected HEAD is preserved, never silently replaced

#### Scenario: Integration continuation follows Git containment

- **WHEN** a Work Lane HEAD is already contained in the candidate but not accepted
- **THEN** lane status selects accepted closeout instead of repeating land
- **WHEN** the Work Lane HEAD is contained in accepted
- **THEN** lane status selects the existing landed-retirement preview
- **AND** retirement still reviews nontracked content and rechecks exact authority
- **AND** an absent candidate does not turn already accepted content into an
  authoring or coordination failure
- **AND** uncommitted lane content remains authoring work, not a retirement cue
- **AND** a lane ahead of candidate continues to select land

#### Scenario: Nontracked content requires an explicit disposition

- **WHEN** a linked worktree contains nontracked content, including ignored evidence
- **THEN** automatic retirement preserves the worktree, refs, Lease and content
- **AND** the preview reports its native footprints and existing lifecycle labels
- **AND** neither Git ignore rules nor a lifecycle label authorize deletion
- **AND** continuation requests existing exact content review before separately authorized disposal
- **AND** required custody is preserved outside the retiring resource before disposal

#### Scenario: Nontracked content appears after planning

- **WHEN** ignored content appears before an unreviewed retirement effect or receipt recovery
- **THEN** fresh effect admission refuses deletion and selects a new content review
- **AND** a reviewed receipt still refuses changed content, foreign ownership and active consumers

#### Scenario: Reviewed content remains inspectable without repeating its manifest

- **WHEN** an owned lane's reviewed tree contains many generated and nontracked nodes
- **THEN** the public preview gives its exact receipt and bounded review summary, not a second copy of the complete manifest
- **AND** the receipt retains every reviewed node for inspection and effect-time drift checks
- **AND** the summary alone never authorizes disposal

#### Scenario: Unrelated native file-descriptor churn is not a retirement consumer

- **WHEN** unrelated processes close descriptors during selected content retirement
- **THEN** the native observer scopes its search to the worktree and external Git index
- **AND** cwd, file, mapping, writer, hardlink and index holders still block deletion
- **AND** an already absent reviewed worktree is not a deletion target; its surviving index remains observed
- **AND** an observation that an unreadable record leaves incomplete is taken again, at most three times within the observer's one 30-second timeout
- **AND** a present unsafe worktree, missing index, incomplete output, a permission failure inside an otherwise inspected process, or a timeout remains unknown
- **AND** reviewed content is rechecked after the process observation

#### Scenario: Processes outside the inspection boundary are reported, not hidden

- **WHEN** a content admission observes open files while processes the invoking user may not inspect are running
- **THEN** the observation covers only the processes the invoking user may inspect
- **AND** a process that denies every `/proc` entry the observer reads, its descriptor links and threads' entries included, is reported once as uninspectable by process ID, user ID and command, not as a consumer
- **AND** where the platform omits uninspectable processes without a record, the report marks their list unavailable rather than empty
- **AND** each content admission records its observation in the progress it produces
- **AND** the terminal receipt and result carry the observation of the admission that removed the worktree, including after recovery

#### Scenario: Exact Lease observation changed after planning

- **WHEN** a planned live or expired Lease differs in lane ref, holder ref,
  generation, or expiry at effect time
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current Lease intact.

#### Scenario: A Lease appears after an absent observation

- **WHEN** landed retirement planned against an absent Lease and a row for the
  target lane exists when the SQLite transaction re-observes it
- **THEN** ETHOS blocks the effect
- **AND** it does not delete the linked worktree, branch, or new Lease.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite Lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS re-observes the ref, worktree, and Lease postconditions
- **AND** it reports the exact non-terminal state without claiming retirement.

### Requirement: Retirement modes preserve distinct authority

Landed retirement of accepted content SHALL be Commitment-free and deletion-only,
accepting exact valid, expired or absent Lease observations with effect-time
rechecks. Superseded retirement SHALL retain selected proof, transient Commitment,
absorption authority and valid Lease. Neither mode SHALL silently consume the
other's authority.

#### Scenario: Landed and superseded commands share one owner

- **WHEN** a caller invokes ordinary landed or superseded linked retirement
- **THEN** both CLI commands construct the same strict request model and call
  the same linked-retirement effect
- **AND** the plan records the selected retirement mode so landed cleanup cannot
  consume superseded proof authority and superseded retirement cannot silently
  weaken to deletion-only admission
- **AND** no wrapper, re-export, compatibility summary, or parallel Python
  effect remains.

### Requirement: Partial superseded retirement restores exact coordinates

When failed superseded retirement leaves an exact ref and valid Lease but no
worktree, its existing recovery MAY recreate the exact branch-bound path. Before
creation, revalidate ref/HEAD/tree, proof/Commitment, four-field Lease, actor,
absence/registration and absorption authority. A later block SHALL preserve the
recovered worktree or report exact compensation failure.

#### Scenario: Exact partial superseded retirement recovers and retires

- **GIVEN** a `work/*` ref remains at the planned Git HEAD and tree
- **AND** its valid Lease is held by the invoking actor
- **AND** the prior linked path is absent and not registered or reused
- **AND** accepted truth exactly absorbs the lane semantics
- **WHEN** the owner supplies that path to authorized superseded retirement
- **THEN** dry-run reports recovery and retirement readiness without mutation
- **AND** apply recreates the exact linked worktree and resumes the existing
  linked retirement effect
- **AND** terminal success requires the Lease, ref, and worktree all absent.

#### Scenario: Partial recovery coordinates drift

- **WHEN** the path collides, the ref moves, the Lease or tree changes, the
  Commitment cannot be verified, or the actor is not the current holder
- **THEN** ETHOS blocks before recreating a worktree
- **AND** it preserves the current ref and Lease unchanged.

#### Scenario: Retirement blocks after recovery

- **WHEN** exact worktree recovery succeeds but the subsequent ref transaction
  or Lease closeout blocks
- **THEN** ETHOS leaves the exact recovered linked worktree available for the
  normal public retry path
- **AND** it reports the failing transition and observed native carrier states
  without claiming retirement.

### Requirement: Lease generation identity is complete across boundaries

Every status, handoff, retirement, receipt and effect SHALL bind a Lease by
exactly lane ref, holder ref, positive generation and expiry. Incomplete or stale
bindings SHALL fail. Lease SHALL NOT store another ID/fingerprint, Git coordinate,
Commitment, workflow field or outcome. Git HEAD/tree, package identity and effect
evidence SHALL remain independently bound by native facts, content identities
and Attestations.

#### Scenario: A boundary omits or changes a Lease fact

- **WHEN** an otherwise matching Lease binding omits or changes lane ref, holder
  ref, generation, or expiry
- **THEN** ETHOS rejects the handoff, retirement, or mutation effect
- **AND** the current Lease and Git carriers remain unchanged.

#### Scenario: Unavailable-holder recovery is admitted

- **WHEN** accepted policy admits unavailable-holder retirement for one complete
  foreign Lease generation
- **THEN** ETHOS calls the same exact revoke primitive used by ordinary holder
  relinquishment
- **AND** no unavailable-holder wrapper or parallel destructive effect exists.

#### Scenario: Cross-host destination import is acknowledged

- **WHEN** the package target actor imports one verified handoff package
- **THEN** ETHOS creates one destination-local Lease generation
- **AND** its content-addressed acknowledgement binds the package identity and
  exact source Git facts separately from the destination lane ref, holder ref,
  generation, and expiry
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
  Lease generation as a string or boolean, or a Git object ID of intermediate
  width
- **THEN** both the typed contract and its JSON Schema boundary reject it
- **AND** no lifecycle effect begins.

### Requirement: Protected-ref semantics are candidate-commit bound

Protected-ref transitions SHALL run admission from the Git-common selected
immutable runtime in isolated mode and SHALL read candidate policy from the
candidate HEAD's committed tree. They SHALL reject ignored candidate runtimes,
accepted-checkout interpreters, inherited `PYTHONPATH`, and missing or mismatched
committed policy inputs. The proof floor SHALL match the committed repository
role.

#### Scenario: Candidate runtime state attempts to override committed semantics

- **WHEN** a candidate ignored interpreter, inherited `PYTHONPATH`, accepted
  interpreter, or uncommitted policy file differs from the candidate HEAD
- **THEN** the protected-ref transition does not execute or read that state
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
historical file set into Work Lane rebase execution. Every rebase conflict SHALL
remain blocked for explicit resolution.

#### Scenario: Historical one-off conflict shape reappears

- **WHEN** a rebase conflict matches a retired Claim-specific file set
- **THEN** ETHOS does not auto-resolve it from the historical Claim or archive
- **AND** the replay fails closed with `refresh_base_failed`.

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

The peer collection SHALL alone own topology; one typed full-ref resolver SHALL
own kind/role; one TransitionPlan compiler SHALL bind local objects, proof
Attestation, exact targets and effects; one Git executor SHALL own live remote
observation, exact CAS, readback and partial-effect Attestation. CLI and hooks
SHALL consume these owners, not recreate branch parsing, proof selection, peer
reconciliation or object-identity policy.

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

Recovery SHALL preserve each distinct obligation within its source boundary and
classify it as accepted, superseded, pending verification or rejected. Accepted
items SHALL map to one current owner, acceptance boundary and proof path; other
outcomes SHALL retain reasons in the governing Change. Conversations, summaries,
temporary files and generated classifications SHALL NOT become authority.

#### Scenario: Current and predecessor tasks are recovered

- **WHEN** a bounded recovery includes a current ETHOS task and its confirmed
  predecessor lineage
- **THEN** distinct semantic obligations from both sources SHALL be adjudicated
  against the same current product model
- **AND** neither task transcript nor an agent-generated summary SHALL become a
  current repository truth store

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** every distinct semantic obligation SHALL remain represented in the
  bounded recovery
- **AND** selections MAY feed disjoint future official OpenSpec Changes without
  creating a mutable feedback queue

#### Scenario: Accepted meaning reaches its final owner

- **WHEN** a recovered obligation is accepted
- **THEN** current product meaning SHALL be placed in the Product Design
  Contract, unfinished dependency order and exit evidence in the Terminal
  Governance Product Design, executable behavior in its native source, schema,
  rule, or test owner, and only irreducible cross-Change rationale in a Decision
  Record
- **AND** the official recovery Change SHALL record the migration and its proof
  without becoming the active product model after archive

#### Scenario: Recovery encounters an unresolved contradiction

- **WHEN** two current obligations cannot be reconciled without changing the
  product model or the available evidence cannot establish the governing fact
- **THEN** the item SHALL remain pending verification or SHALL raise a model gap
- **AND** no guessed resolution SHALL authorize implementation or deletion

### Requirement: Feedback interpretation preserves source authority

Direct human guidance SHALL remain design input. Later explicit guidance
supersedes earlier guidance only on the same subject. Delegated fact, inference
and remedy SHALL be evaluated separately; rejecting a model does not invalidate
its observation. Repository history SHALL prove implementation, not human intent.

#### Scenario: Delegated feedback mixes evidence and remedy

- **WHEN** an adopter or another agent reports an exact observation together
  with an inferred cause or proposed design
- **THEN** the observation, inference, and remedy SHALL be evaluated separately
- **AND** accepting the observation SHALL NOT automatically admit the proposed
  entity, state, or compatibility mechanism

### Requirement: Recovery material does not become another lifecycle

New input SHALL NOT implicitly expand an active Change. Convergence SHALL NOT
create a second carrier for product meaning, order, lineage, predecessors,
successors, hypotheses, experiments, coverage or scope/granularity. Temporary
material SHALL retire after accepted meaning and necessary rationale reach their
unique owners and coverage is verified.

#### Scenario: Recovery input is temporary

- **WHEN** raw transcripts, extracted records, classification scripts, or
  intermediate matrices were created outside tracked repository authority
- **THEN** they SHALL authorize no product or lifecycle action
- **AND** they SHALL be deleted after source-boundary, disposition, destination,
  and coverage proof no longer depend on them

#### Scenario: A Change's scope or granularity is evaluated

- **WHEN** a proposed obligation is considered for an active Change
- **THEN** it SHALL be admitted only when its intent, implementation, proof, and
  closeout form one reviewable outcome
- **AND** unrelated intent SHALL become a separate official Change or a
  non-authorizing Attestation rather than expanding the active Change

#### Scenario: Lineage and experimental reasoning are audited

- **WHEN** convergence audits predecessors, successors, hypotheses,
  experiments, or requirement coverage
- **THEN** it SHALL identify the existing source owner and whether a public
  derived view is actually available
- **AND** it SHALL NOT create a mutable Change DAG, hypothesis registry,
  experiment ledger, successor back-link, or replacement carrier when that view
  is absent

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

One verified OpenSpec lifecycle-effect authority SHALL cover archive, canonical
spec projection and post-archive closeout. It SHALL bind repository identity,
transient Commitment digest, prior/resulting Git facts, exact paths, official
result and terminal effect Attestation. Status/plan/prove/land/prewrite/hooks
SHALL consume it unchanged. Durable partial effects SHALL recover through the
same public operation and exact CAS.

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
- **THEN** it retains the selected runtime and every generation referenced by effective config, live process commands or native linked interpreter bindings
- **AND** historical operation and diagnostic records do not create executable dependencies merely by naming a generation
- **AND** current operation recovery consumes the selected runtime rather than treating historical observations as activation authority.

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

A complete official planning graph with explicit `skip_specs: true` and no deltas
SHALL compile deterministic, non-empty acceptance from official projections only.
Metadata, proposal, design and task meaning SHALL survive; checkbox progress
SHALL not affect acceptance. Bounded implementation admission SHALL require
neither completed tasks, fake requirements, `commitment.toml` nor another tracked
intent carrier.

#### Scenario: Planned spec-free Change is selected before implementation

- **GIVEN** the official OpenSpec projection declares `skip_specs: true`
- **AND** its required proposal, design, and tasks artifacts are present and valid
- **AND** it contains no requirement deltas
- **AND** one or more implementation tasks remain incomplete
- **WHEN** ETHOS compiles the selected Change
- **THEN** it produces one deterministic non-empty transient Commitment
- **AND** that Commitment can authorize bounded implementation paths through the ordinary current resolver.

#### Scenario: Task progress does not mutate acceptance identity

- **GIVEN** a valid spec-free Change whose task descriptions are unchanged
- **WHEN** task checkboxes advance from incomplete to complete
- **THEN** the compiled Commitment digest remains unchanged
- **AND** OpenSpec task progress remains available independently for proof and closeout admission.

#### Scenario: Completed spec-free Change is selected

- **GIVEN** a valid spec-free Change whose required tasks are complete
- **WHEN** ETHOS proves and archives the selected Change
- **THEN** its Commitment remains applicable through the attested official archive transition
- **AND** closeout does not reconstruct authority from archived task progress.

#### Scenario: Empty deltas are not implicitly accepted

- **WHEN** a Change has no requirement deltas but lacks the official spec-free declaration or a complete valid planning artifact graph
- **THEN** ETHOS fails closed with the exact OpenSpec acceptance gap
- **AND** no filename pattern, product category, compatibility carrier, task progress state, or archived directory grants authority.

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid Lease SHALL create and complete one selected
official Change before Commitment compilation. Selection SHALL consume exact
active identity and official artifact outputs, including when other Changes
coexist. Only those outputs are admitted; directory-wide authority is excluded.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design,
  tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier
  is admitted.

#### Scenario: Exact absent Change root resolves to metadata bootstrap

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no active official Change exists
- **WHEN** prewrite receives exactly `openspec/changes/<change>` for an absent,
  valid Change identifier
- **THEN** it returns a structured block rather than directory write authority
- **AND** its unique next action is the exact prewrite command for
  `openspec/changes/<change>/.openspec.yaml`
- **AND** it does not select archived Change authority.

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient
  Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path
  attribution
- **AND** bootstrap authority grants no additional scope or durable permission.

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** the request cannot select one active Change, an identifier is
  invalid, or a requested path is outside the selected official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does
  not authorize the write.

#### Scenario: Official creation coexists with another active Change

- **GIVEN** official new-change execution creates metadata beside another active Change
- **WHEN** every prewrite path belongs to that one existing active Change root
- **THEN** current resolution selects it and consumes its official artifact graph
- **AND** public prewrite, pre-tool and Git commit use the same admission owner
- **AND** a missing or mismatched Lease still rejects the request

#### Scenario: Ordinary work remains ambiguous

- **WHEN** product paths or several Change roots cannot identify one selected intent
- **THEN** ETHOS keeps the unresolved intent gap and marks the choice as required
- **AND** its next action inspects the official Change list rather than repeating status
- **AND** explicit plan and proof selection remain bound to the named official intent

#### Scenario: Canonical INFO does not monopolize unrelated authoring

- **GIVEN** one selected valid active Change and an owned Work Lane with a current Lease
- **AND** official validation succeeds with only blocking INFO findings in existing canonical specs
- **WHEN** prewrite requests ordinary paths disjoint from those exact spec repairs
- **THEN** ETHOS applies the selected Change's fresh ordinary material scope and all other prewrite controls, without granting paths from the INFO finding
- **AND** status, plan, proof and closeout retain the canonical INFO gaps until corrected
- **AND** a mixed repair-and-ordinary request, invalid validation, missing Commitment or uncovered path remains blocked

### Requirement: Remote publication observations preserve epistemic state

The existing remote-publication effect adapter SHALL be the sole owner of
bounded live remote-ref observation for exact publication. It SHALL preserve
whether a target ref is present, absent, unavailable, or not observed because
an earlier publication precondition failed. Public CLI and Git hooks SHALL
consume only complete observations and SHALL NOT recreate availability,
ancestry, or object-identity judgments from missing coordinates.

#### Scenario: exact publication uses the target observer

- **WHEN** `ethos publish --ref <full-ref> --probe-remote` evaluates declared peers
- **THEN** the remote-effect adapter SHALL perform one bounded observation for
  each exact peer/ref target
- **AND** remote-tracking state or general reachability SHALL NOT substitute for
  that exact ref fact.

#### Scenario: publication fails before remote observation

- **WHEN** source trust, source identity, or another pre-observation
  publication precondition fails
- **THEN** publication SHALL return a structured non-passing result with that
  exact upstream gap
- **AND** it SHALL NOT index, synthesize, or report a remote object OID.

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

### Requirement: Archive authority survives an authorized base refresh

ETHOS SHALL preserve the exact archived Change authority when an authorized
Work Lane base refresh rewrites the archive commit. The recovered authority
MUST be derived from the existing archive effect and exact refresh evidence,
and MUST remain bound to the same Change identity and archive post-image.

#### Scenario: Archived lane is refreshed onto a newer candidate

- **GIVEN** a Work Lane archived one official OpenSpec Change through an
  attested archive effect
- **AND** an authorized base refresh rewrote that archive commit onto a newer
  candidate
- **WHEN** ETHOS resolves archive authority for the refreshed Work Lane
- **THEN** it derives the rewritten archive tip from the archive and refresh
  Attestations
- **AND** it recognizes the same archived Change and post-image as authority

#### Scenario: A nearer unrelated archive exists after refresh

- **GIVEN** the refreshed Work Lane history contains an archive for another
  Change nearer to `HEAD`
- **WHEN** ETHOS resolves archive authority for the Work Lane's archived Change
- **THEN** it MUST NOT substitute the unrelated archive
- **AND** proof planning remains bound to the Work Lane's exact archived Change

#### Scenario: Refresh evidence is missing or ambiguous

- **WHEN** ETHOS cannot derive one exact rewritten archive tip from valid
  archive and refresh Attestations
- **THEN** archive authority resolution fails closed
- **AND** ETHOS does not infer continuity from content similarity, patch
  identity, path proximity, or another archived Change

### Requirement: Minimal Decision Rationale Preservation

ETHOS SHALL retain a decision record only when deleting it would erase
cross-Change rationale not carried by the current semantic owner. A record
explains why; it SHALL NOT own current product behavior or workflow state.
Its positive four-digit number SHALL remain stable and SHALL NOT be reused for
a different ruling. Its semantic topic MAY change with repaired links.

#### Scenario: Historical decision material is evaluated

- **WHEN** a removed decision subsystem contains rationale from several files
- **THEN** semantically distinct alternatives, consequences and revisit
  conditions are retained; overlapping or fully absorbed records are removed

#### Scenario: Decision rationale uses the minimum physical shape

- **WHEN** more than one decision rationale is retained under `docs/decisions/`
- **THEN** `dr-<four-digit-id>-<semantic-topic>.md` records remain directly navigable from
  `docs/decisions/README.md`, which explains the directory's role
- **AND** `docs/README.md` routes readers to that entrance instead of copying
  the record list
- **AND** the entrance is not a decision registry, runtime authority, or
  reason to add a template, schema, lifecycle directory, or duplicate catalog

#### Scenario: Decision identity is missing or duplicated

- **WHEN** a `role: decision` record in the selected documentation root has no
  stable numbered filename or shares its number with another current record
- **THEN** the Docs Registry blocks that exact source or conflicting pair
- **AND** a historical retired number is never assigned to a different ruling;
  current-tree uniqueness alone does not establish that historical fact

#### Scenario: Current authority is resolved

- **WHEN** a reader opens a decision record
- **THEN** it identifies the current semantic owner
- **AND** current behavior is determined by that owner, not historical rationale

#### Scenario: Decision identity and disposition agree across native carriers

- **WHEN** the Docs Registry reads a `role: decision` document under any selected root
- **THEN** its filename, `decision_id`, and sole document-level title identify the same positive ruling
- **AND** `decision_status: accepted` and `state: canonical` distinguish decision disposition from document classification without claiming implementation acceptance or authority
- **AND** malformed metadata, duplicate identities and contradictory carriers block without mutating source

#### Scenario: Rationale remains distinct from an execution procedure

- **WHEN** a decision record is validated through the shared native documentation owner
- **THEN** its only sections are Context, Decision, Alternatives Rejected, Consequences and Boundary, and Evidence and Revisit, in that order, each with readable rationale
- **AND** ordinary prose, rationale lists, quotations, tables, bare paths and evidence links remain valid
- **AND** task progress, code blocks, extra HTML, nested or extra headings and executable procedures cannot impersonate decision rationale
- **AND** syntax inspection never evaluates commands or ambient variables, preserves unresolved invocation ambiguity, and does not certify decision quality or current delivery
- **AND** ETHOS's own retained rationale migrates to the same form without losing alternatives, costs, boundaries, historical dates, evidence or revisit conditions

### Requirement: Singular Documentation Entrypoint

ETHOS SHALL expose `docs/README.md` as its sole current documentation
entrypoint.

#### Scenario: Current documentation is traversed

- **WHEN** a current source, policy, or documentation carrier links to the
  documentation entrypoint
- **THEN** it SHALL link to `docs/README.md`
- **AND** `docs/index.md` SHALL be absent
- **AND** immutable historical evidence MAY retain the path observations that
  were true when it was recorded.

#### Scenario: An adopter uses the portable Docs Registry

- **WHEN** ETHOS audits an adopted repository
- **THEN** the adopter SHALL NOT be required to reproduce ETHOS's
  `docs/decisions/` directory or root documentation filename
- **AND** portable subject, role, state, and relation semantics SHALL remain the
  shared contract.

### Requirement: Semantic Reference Closure Distinguishes Use From Assertion

ETHOS SHALL classify a retired path as a current consumer only when a current
carrier uses that path as an executable, import, configuration, declaration, or
navigable reference. A normative statement, test assertion, or explanatory
mention that requires or reports the path's absence SHALL NOT itself constitute
consumption.

#### Scenario: Canonical specification requires absence

- **WHEN** an official canonical OpenSpec requirement names a retired path only
  to require that the path be absent
- **THEN** repository semantic closure SHALL NOT report that specification as a
  consumer of the retired path
- **AND** the independent absence check SHALL remain enforceable.

#### Scenario: Canonical specification links to a retired path

- **WHEN** an official canonical OpenSpec specification contains a navigable
  link whose resolved destination is a retired path
- **THEN** repository semantic closure SHALL report the specification as a
  current consumer of that retired path.

#### Scenario: Executable consumer remains

- **WHEN** current source, configuration, import syntax, command syntax, or a
  declared runtime owner resolves a retired path
- **THEN** repository semantic closure SHALL report the exact consumer
- **AND** prose polarity SHALL NOT suppress that executable relation.

### Requirement: Destructive Work Lane retirement is a resumable observed transition

Authorized retirement SHALL be one receipt-bound transition over exact worktree,
ref and Lease. Before effects, persist the immutable request and verify surviving
control root, Git binary, every process cwd, ref/HEAD, cleanliness, Lease and actor
authority. After each attempt, native observations SHALL determine completed and
remaining effects, not process flags. Revoke Lease only after worktree/ref absence.

#### Scenario: Execution coordinates fail before destruction

- **WHEN** Git cannot be resolved or the surviving control root and effect
  working directories cannot be used before an authorized retirement
- **THEN** ETHOS blocks before removing the worktree, branch ref, or Lease
- **AND** the structured result identifies the failed preflight coordinate.

#### Scenario: Failure follows worktree removal

- **WHEN** the exact worktree is removed and a later ref effect cannot start or
  complete
- **THEN** ETHOS reports `state=partial_transition`
- **AND** the durable progress receipt reports worktree removal as complete and
  ref deletion and Lease revocation as remaining
- **AND** no later process is launched from the removed worktree.

#### Scenario: Recovery converges from native carrier facts

- **WHEN** an authorized caller supplies an exact current retirement receipt
  after a partial effect
- **THEN** ETHOS re-observes the surviving control root, ref, worktree, and Lease
- **AND** it applies only the effects still required for the declared terminal
  state
- **AND** a repeated recovery of the same terminal request is recognized as
  complete without a second destructive effect.

#### Scenario: Recovery authority or coordinates are ambiguous

- **WHEN** the request bytes, repository identity, target HEAD, accepted
  authority, or caller authority differ from the receipt, or a valid Lease is
  held by another actor
- **THEN** ETHOS fails closed without changing any carrier
- **AND** it does not reinterpret an old receipt or mint replacement authority.

### Requirement: Abandonment uses the sole retirement transition owner

ETHOS SHALL expose explicit abandonment of a clean divergent Work Lane through
the same retirement request, observation, reducer, effect executor, and progress
receipt used by linked retirement. The repository SHALL retain no independent
abandonment mutation engine or compatibility reader for retired receipt
schemas.

#### Scenario: Owner-authorized clean divergent lane is abandoned

- **WHEN** the exact holder authorizes abandonment of its clean divergent
  `work/*` Lane with a valid Lease and a structured reason
- **THEN** ETHOS derives an immutable request and may converge the worktree, ref,
  and Lease to absence through exact effects
- **AND** the terminal receipt binds the reason, authority, original HEAD and
  tree, completed effects, and terminal observations.

#### Scenario: Active foreign ownership remains protected

- **WHEN** a clean divergent Lane has a valid Lease whose holder is not the
  invoking actor
- **THEN** abandonment and recovery both block before effects
- **AND** explicit authorization flags or receipt possession do not substitute
  for holder authority.

### Requirement: Commit policy applies to exact introduced commit ranges

ETHOS SHALL compile the commit policy, the paradigm's subject grammar and SSH
signature with the optional tracked `.ethos/workspace.toml [commit_policy]`
declaration, through the existing repository-policy owner and apply that
compiled policy only to the commits newly introduced by one proposed Git ref
update. The range projection SHALL be provider-neutral, SHALL preserve the
repository object format, and SHALL NOT reinterpret or revalidate commits
already reachable from the trusted baseline.

#### Scenario: Existing ref receives a normal fast-forward

- **WHEN** a non-delete update supplies readable remote and proposed commit
  objects
- **THEN** ETHOS validates each commit reachable from the proposed commit but
  not from the remote commit in deterministic oldest-first order
- **AND** commits already reachable from the remote commit are not revalidated.

#### Scenario: Existing ref receives a non-fast-forward update

- **WHEN** the proposed commit does not descend from the readable remote commit
- **THEN** ETHOS still reports and validates exactly the commits newly reachable
  from the proposed commit
- **AND** the existing topology and ref-movement policy independently decides
  whether the non-fast-forward effect is admissible.

#### Scenario: A new proposal ref has a trusted accepted baseline

- **WHEN** the remote object ID is the repository-native zero object ID and the
  target has proposal role
- **THEN** ETHOS resolves the declared remote's accepted ref as the trusted
  baseline and validates only the proposed commits not reachable from it
- **AND** it blocks if that baseline is absent, unreadable, or not an ancestor of
  the proposed commit.

#### Scenario: A new non-proposal ref has no trustworthy baseline

- **WHEN** the remote object ID is zero and no exact trusted baseline is supplied
  or derivable for the target
- **THEN** ETHOS fails closed with a baseline gap
- **AND** it does not substitute the root commit or scan all repository history.

#### Scenario: An accepted or release object is projected to an absent ref

- **WHEN** an accepted branch, release branch, or annotated release tag has a
  zero remote object ID
- **AND** the exact proposed commit has one valid accepted-closeout Attestation
- **THEN** ETHOS uses that Attestation's accepted pre-state as the trusted
  historical baseline
- **AND** local publication dry-run and the real pre-push transport validate the
  same introduced revisions without trusting another remote or an unrelated
  sibling ref.

#### Scenario: A delete update is observed

- **WHEN** the proposed object ID is the repository-native zero object ID
- **THEN** commit-range admission reports a no-range delete result
- **AND** it leaves deletion authority to the existing ref policy.

#### Scenario: An annotated tag is proposed

- **WHEN** either endpoint names an annotated tag object
- **THEN** range admission peels that endpoint to its exact commit before
  deriving introduced commits
- **AND** tag-object trust remains governed by the existing publication owner.

#### Scenario: Commit policy is absent or malformed at the proposed tip

- **WHEN** the proposed committed tree contains no `[commit_policy]` table
- **THEN** ETHOS applies the paradigm's subject grammar and SSH signature to the
  introduced range
- **AND** when the table is present but malformed, admission fails closed before
  returning a passing range result.

### Requirement: Commit signature declaration and signer trust remain distinct

For commit-range admission, the paradigm's SSH signature SHALL govern the
presence and format of the signature embedded in each introduced commit.
Signer authorization and trust-anchor verification SHALL remain a separate
operation-specific observation and SHALL NOT require a repository-tracked key
list or provider-specific policy parser.

#### Scenario: A declared signature is missing or has the wrong format

- **WHEN** an introduced commit lacks a signature or carries a format other
  than SSH
- **THEN** the shared range validator reports the exact commit and signature gap
- **AND** local push admission and hosted CI reach the same verdict.

#### Scenario: A lifecycle operation creates or replays commits

- **WHEN** ETHOS itself creates or replays an object
- **THEN** it uses the same subject and signature-format validator
- **AND** its existing local trust verifier additionally proves the configured
  signer before any ref, Lease, or worktree effect is retained.

### Requirement: Absorbed local resource retirement is independent of authoring role

ETHOS SHALL admit deletion-only retirement of an explicit local topic ref whose
exact HEAD equals or precedes accepted truth, regardless of authoring prefix.
Accepted, release and candidate resources remain excluded. Existing actor,
Lease, cleanliness, exact-CAS, readback and recovery obligations SHALL hold.
This path SHALL grant neither source-write authority nor remote-review cleanup.

#### Scenario: An absorbed unlinked topic ref predates current policy

- **WHEN** an authorized caller selects an exact unlinked, unleased topic ref
  absorbed by the exact current accepted HEAD
- **THEN** the public absorbed-ref retirement and installed reference-transaction
  hook admit the same exact deletion under current accepted policy
- **AND** the old object need not contain the current repository policy schema
- **AND** the command attests ref absence without changing repository roots.

#### Scenario: A clean linked topic worktree is already absorbed

- **WHEN** an authorized caller selects an exact clean linked topic worktree
  absorbed by accepted truth with no valid foreign Lease
- **THEN** public landed retirement removes only that worktree and ref through
  the existing observed retirement operation
- **AND** it preserves exact-generation Lease handling and resumable failures.

#### Scenario: Eligibility does not grant arbitrary deletion

- **WHEN** the target is a repository root, dirty, not absorbed, held by a valid
  foreign Lease, or differs from the admitted exact coordinates
- **THEN** retirement blocks before destructive effects and preserves the target
- **AND** a bare ref deletion without prepared retirement intent cannot use this
  public retirement authority.

### Requirement: Missing Work Lane coordination is reacquired without content mutation

The public Lease lifecycle SHALL reacquire missing coordination from fresh exact
linked-lane, actor, HEAD, index, working-content digest and absence facts. Apply
SHALL require explicit authorization and matching coordinates, use the four-field
Lease transaction, preserve all Git/content and record or recover its native
effect Attestation. The resulting Lease SHALL NOT imply intent, proof or write
admission.

#### Scenario: Dirty linked Work Lane has lost its Lease

- **WHEN** an explicitly selected registered Work Lane has no Lease and contains
  staged, unstaged, and untracked content
- **THEN** dry-run returns one exact reacquisition command without modifying it
- **AND** authorized apply acquires coordination for the invoking holder while
  retaining the same HEAD, index, and content bytes.

#### Scenario: Exact coordinates drift or a different owner appears

- **WHEN** the target HEAD, index, content, linkage, or absent-Lease observation
  changes before acquisition commits
- **THEN** ETHOS blocks or rolls back its acquisition without replacing the
  current holder or altering repository content.

#### Scenario: A repeated apply observes the exact valid Lease postimage

- **WHEN** the same exact reacquisition is repeated after its Lease was committed
- **THEN** ETHOS recognizes the current relation without advancing generation
- **AND** reuses matching effect evidence or records the recovered postimage
- **AND** a different generation or expiry is rejected even for the same holder.

#### Scenario: Missing Lease is reported before content admission

- **WHEN** status or prewrite finds a linked Work Lane without a Lease
- **THEN** its actionable guidance selects public reacquisition derivation
- **AND** it does not recommend creating a nested lane or declare content proved.

### Requirement: Retained Topic Retirement

ETHOS SHALL allow an explicitly selected clean local topic to retire without
claiming accepted absorption when every target commit remains reachable from
another explicitly selected, surviving local topic ref. This deletion-only
transition SHALL reuse the existing retirement owner, exact Git effect,
Lease coordination, immutable receipt, and recovery mechanism.

#### Scenario: Redundant clean history is retained by a local descendant

- **WHEN** an authorized actor requests `lane retire superseded` from the
  accepted control root with an exact target HEAD and a distinct local
  `refs/heads/...` retention ref containing that HEAD
- **THEN** the plan binds target deletion, accepted HEAD, retained ref and OID,
  target worktree cleanliness, and current target Lease coordinates
- **AND** successful apply removes only the target worktree, ref, and applicable
  Lease, leaving accepted and retained objects and retained checkout unchanged
- **AND** the result reports history retention rather than accepted semantics

#### Scenario: Retention or deletion coordinates do not hold

- **WHEN** the target is dirty, protected, candidate, stale, or foreign-owned,
  or the retained ref is missing, identical, protected, candidate, or unrelated
- **THEN** retirement fails closed without deleting any target resource

#### Scenario: Retained ref moves after derivation

- **WHEN** the exact retained ref no longer resolves to its planned OID
- **THEN** preflight rejects before worktree removal
- **AND** the Git transaction independently checks the retained-ref assertion
  atomically with deletion, preserving existing partial-effect recovery

#### Scenario: Historical topic lacks current authoring policy

- **WHEN** the accepted owner has admitted one exact retirement intent for a
  historical topic whose own policy cannot be compiled
- **THEN** the reference-transaction hook consumes accepted policy and that exact
  intent without granting authoring rights or accepting a raw unplanned deletion

### Requirement: Historical workspace evidence has no current proof role

ETHOS SHALL evaluate current proof through its existing selected Attestations
and exact operation bindings. The proof floor and repository documentation
audit SHALL operate independently of historical workspace evidence directories.
Git SHALL preserve removed committed records for historical retrieval.

#### Scenario: Historical directories are retired

- **WHEN** reviewed historical evidence and its duplicate documentation are
  removed from the current source tree
- **THEN** current proof consumers retain the same predicate and binding checks
- **AND** no directory-shape gate or required documentation placeholder remains.

#### Scenario: A retirement batch contains many historical paths

- **WHEN** current reference closure audits multiple retired paths
- **THEN** it parses each current path-bearing carrier at most once for that
  retirement audit, independently of the number of retired paths
- **AND** it reports every exact surviving consumer with unchanged relative-link
  and source interpretation.

#### Scenario: A new source file uses an old evidence path

- **WHEN** a maintained source file appears outside the official OpenSpec archive
- **THEN** its ordinary source class and budget apply
- **AND** an old evidence path supplies no automatic historical exclusion.

### Requirement: Reviewed content retirement binds the exact destructive preimage

ETHOS SHALL allow explicitly reviewed historical topics to retire through
existing receipt-bound abandonment/recovery. Selected content, index, root identity, ref, accepted object,
actor and Lease SHALL remain exact inputs. Ignored status SHALL NOT imply disposal
permission, and hashes SHALL NOT claim semantic acceptance.

#### Scenario: Reviewed absorbed lane has residual content

- **WHEN** an operator derives and reviews an exact receipt for a non-protected
  historical topic whose remaining content has been absorbed, superseded or
  explicitly rejected with a reason
- **THEN** explicit authorized application removes only that selected worktree,
  ref and Lease through the existing operation
- **AND** no backup lane, archive directory or parallel lifecycle is created.

#### Scenario: Content or authority changes after review

- **WHEN** the selected filesystem, index, ref, accepted object, actor or Lease
  no longer matches the receipt, or its observation is unsafe or unavailable
- **THEN** retirement stops before the next destructive effect
- **AND** unresolved bytes and current resources remain protected.

#### Scenario: Historical coordination has expired or disappeared

- **WHEN** a reviewed non-protected topic has missing or expired coordination,
  including a historical commit predating the repository adoption profile
- **THEN** an identified operator can derive and authorize exact deletion from
  the current accepted control checkout without recreating a Lease or profile
- **AND** a valid foreign holder or a Lease acquired after derivation blocks
  the old operation before further deletion
- **AND** expired coordination grants neither ordinary ref updates nor deletion
  of additional or unrelated refs.

#### Scenario: Ignored and read-only generated resources are selected

- **WHEN** an exact reviewed inventory includes ignored or read-only resources
  in an owned isolated root with no active consumers
- **THEN** their safe removal is part of that same bounded retirement
- **AND** external link targets and shared file permissions remain unchanged.

#### Scenario: Native node ownership or filesystem boundary is foreign

- **WHEN** a selected root, descendant or index node has a different native
  owner, or its device differs from the containing directory
- **THEN** derivation rejects the node before opening its content or traversing
  it and does not persist a disposal request
- **AND** effect-time observation applies the same admission boundary.

#### Scenario: An admitted retirement is interrupted

- **WHEN** retirement has partially completed and the operator invokes recovery
  with the original exact receipt
- **THEN** current observations select only remaining admitted effects
- **AND** already completed effects are not replayed and new content is not
  deleted under an obsolete receipt.

#### Scenario: Another retirement holds repository coordination

- **WHEN** application or recovery encounters an already-held retirement lock
- **THEN** it promptly returns `lane_retirement_in_progress`, the exact request
  receipt identity and the existing receipt-bound recovery command
- **AND** it makes no content, ref or Lease effects and claims no unobserved
  progress
- **AND** after normal holder exit or process death, recovery reacquires the
  lock and revalidates current facts rather than replaying assumed effects.

#### Scenario: Ref transaction advances during stale-intent reclamation

- **WHEN** reclamation observes an expired issued ref intent but its record is
  renewed or advances to prepared or committed before the existing lock is held
- **THEN** reclamation preserves the current record and reports that it changed
- **AND** unchanged expired issued records remain reclaimable; matching identity
  alone never authorizes deletion of a changed transaction state.

#### Scenario: Ref intent writer exits while holding coordination

- **WHEN** a live writer holds intent coordination, including during cleanup
- **THEN** competing mutations return a bounded timeout and preserve its record
- **AND** normal exit or process death permits a fresh exact claim without
  deleting a live holder's lock or discarding the transaction
- **AND** coordination-file count does not grow with transaction history
- **AND** unavailable native locking prevents mutation rather than silently
  substituting an existence-marker protocol.

### Requirement: Reviewed retirement requires actual writer quiescence

All actual writers SHALL stop before content review; participants SHALL honor
lane coordination through disposal. The operator SHALL verify that handoff.
Lease transfer or an empty process scan SHALL NOT imply stopped writers or
exclude arbitrary uncooperative same-UID writes. Unknown liveness SHALL block
destructive application.

#### Scenario: Actual writer is stopped before reviewed retirement

- **WHEN** a writer still consumes the selected worktree
- **THEN** retirement rejects application and preserves its content and refs
- **AND** after the writer exits, the operator reviews the final exact content
  under current coordination before applying retirement
- **AND** successful application and recovery remove only the reviewed resources.

### Requirement: Reviewed retirement derives only existing native resources

ETHOS SHALL allow existing reviewed-content abandonment to select one registered
detached worktree by exact absolute path. Its immutable receipt SHALL bind the
literal target, native Git registration, detached HEAD, index and content,
accepted object and actor. An absent branch SHALL produce no ref-deletion or
Lease effect. Existing coordinated quiescence, admission, native removal and
monotonic recovery SHALL remain the single protocol.

#### Scenario: Reviewed detached content retires without synthetic authority

- **WHEN** the operator selects a registered detached worktree by absolute path
  and explicitly reviews its final content after actual writers have stopped
- **THEN** ETHOS derives only the exact worktree-removal effect
- **AND** application removes that worktree and registration while preserving
  all refs, Lease rows and other worktrees, including same-HEAD siblings.

#### Scenario: Changed native identity or consumption prevents removal

- **WHEN** the selected path is aliased, reattached, locked, replaced, actively
  consumed, incompletely observable, or differs from the reviewed HEAD, native
  registration, content or index
- **THEN** ETHOS rejects the effect and retains current content
- **AND** changed actor or accepted coordinates also prevent application.

#### Scenario: Detached removal resumes through the same receipt

- **WHEN** a detached retirement is interrupted before native deregistration
  or after its removal is complete
- **THEN** recovery reobserves the same bound resources and executes only
  remaining effects
- **AND** it never deletes replacement bytes, recreates a branch or Lease, or
  replays a completed native removal.

### Requirement: Executable topology policy shares runtime identity

The executable topology declaration SHALL be a native resource of the package
that interprets it. Working-directory and audited-repository files SHALL NOT
replace that runtime policy. Missing or malformed package policy SHALL fail
closed. Successor code and declaration SHALL be validated together while the
installed predecessor continues governing the transition with its own policy.

#### Scenario: Candidate declaration evolves

- **WHEN** the successor changes its topology schema and removes the old carrier
- **THEN** the predecessor continues loading its own package policy
- **AND** the successor loads its own declaration without a compatibility copy
- **AND** normal hooks, intent and fresh mutation admission remain required

#### Scenario: Audited checkout offers an incompatible override

- **WHEN** an unrelated checkout supplies an incompatible topology declaration
- **THEN** public artifact observation still uses the executing package policy
- **AND** it does not parse that checkout declaration as its executable policy

### Requirement: Artifact origin is independent of presentation

Artifact admission SHALL derive generation ownership from native producer
declarations or lifecycle ownership, not filename suffix, format ownership,
tracking or existence alone. Without that evidence it SHALL retain unclassified
origin and apply ordinary source admission independently of placement rules.

#### Scenario: Authored native configuration

- **WHEN** an owned lane requests a native configuration with no generated owner
- **THEN** its serialization format does not create a generated-artifact rejection
- **AND** ordinary intent, containment and authority checks remain required

#### Scenario: Missing path

- **WHEN** a requested path does not exist
- **THEN** admission reports absence separately from ownership
- **AND** absence does not prove generation, successful deletion or consumer closure

### Requirement: Native generated projections retain one producer

Generated projection admission SHALL use the declared source/output relation and
the native producer's verification semantics. It SHALL distinguish source inputs
from generated outputs and reject an unverifiable or conflicting owner rather
than silently admit a manual output edit.

#### Scenario: Generated output edit

- **WHEN** an exact patch changes a declared output inconsistently with its source
- **THEN** admission blocks with the producer and output identified
- **AND** an output matching the same patch's source passes that projection check

#### Scenario: Source model is authored

- **WHEN** a projection input and output share a formatter or file family
- **THEN** only the declared output is classified as producer-owned
- **AND** formatter assignment creates no generation authority

#### Scenario: Projection ownership is retired

- **WHEN** an exact patch removes an output and its producer relation coherently
- **THEN** admission evaluates surviving consumers and permits a closed retirement
- **AND** removing only the declaration cannot silently authorize arbitrary output bytes

#### Scenario: Git commit evaluates its prospective index

- **WHEN** the Git pre-commit transport checks a generated projection
- **THEN** it obtains producer and output bytes from the exact staged tree
- **AND** unstaged source or output changes cannot alter that verdict
- **AND** it consumes the same producer and deletion semantics as patch admission
- **AND** changed HEAD or index coordinates invalidate the in-flight observation

### Requirement: Deletion admission preserves affected consumers

Exact patch admission SHALL retain deleted paths and evaluate affected surviving
native consumers against the effective postimage. It SHALL permit removal with
consumer updates, reject a surviving required input and preserve unknown coverage
when the required native relationship cannot be resolved.

#### Scenario: Authored configuration and consumer retire together

- **WHEN** a patch removes configuration and updates its explicit native consumer
- **THEN** no generation exception is needed and the closed deletion is admitted
- **AND** preimages, caller ownership and exact paths remain checked

#### Scenario: Required native consumer survives

- **WHEN** a patch removes a file still selected as an explicit native input
- **THEN** admission blocks and names the deleted input and surviving consumer
- **AND** unchanged consumers are not omitted because they have no patch entry

### Requirement: Artifact admission failures identify a usable continuation

Public artifact admission SHALL distinguish ownership, existence, placement and
proposed effect. A failure SHALL expose the relevant boundary and one next
observation or exact patch command; it SHALL NOT suggest replaying an unchanged
request as a repair.

#### Scenario: Producer output lacks an exact proposed effect

- **WHEN** output admission requires verification but no patch is supplied
- **THEN** the result requests an exact patch with current root and paths
- **AND** it does not claim any mutation occurred

#### Scenario: Invalid working declaration is repaired

- **WHEN** a producer declaration has invalid uncommitted syntax
- **THEN** public admission identifies an exact repair-patch continuation
- **AND** it permits a valid postimage only after retaining known baseline owners
- **AND** unrelated changes cannot use invalid ownership as permission

### Requirement: Signature-only payload preservation

ETHOS SHALL compare signature replacements by exact complete commit bytes after
removing only Git signature headers and their continuation lines. Tree, ordered
parents, author, committer, dates, encoding, unknown headers and message bytes
SHALL remain unchanged. Same-tree or normalized-text equality SHALL NOT establish
signature-only equivalence.

#### Scenario: Non-signature header bytes differ

- **WHEN** a replacement adds or removes a carriage return in an encoding header
- **THEN** signature-only equivalence is false
- **AND** no payload normalization conceals the difference

#### Scenario: Only signature headers differ

- **WHEN** distinct commits have identical complete non-signature payloads
- **THEN** the payload comparator reports signature-only equivalence
- **AND** separate current trust verification is still required before repair

#### Scenario: Root and merge commit payloads are preserved

- **WHEN** repair creates a replacement for a root or merge commit
- **THEN** its zero or multiple ordered parents and complete payload remain exact
- **AND** unsupported native signing inputs fail without moving refs

### Requirement: Bounded accepted signature replacement

ETHOS SHALL admit replacement only from the current accepted policy, explicit
authorization, an exact unsigned source, a trusted signed replacement, selected
ref coordinates and clean linked worktrees. Each effect SHALL recheck its own
preconditions. Existing effect evidence SHALL support recovery without becoming
reusable authorization.

#### Scenario: Select only required local refs

- **WHEN** current policy identifies the accepted ref and coupled local projections
- **THEN** the plan binds every selected ref to its observed old and desired OID
- **AND** independent release, topic and remote refs remain unchanged
- **AND** an unrelated candidate OID is neither overwritten nor silently included

#### Scenario: Trust and payload are independent conditions

- **WHEN** a replacement has a trusted signature but different preserved bytes
- **THEN** repair rejects it
- **AND** an equal payload with an untrusted signature is also rejected

#### Scenario: Drift blocks the next effect

- **WHEN** a bound ref, policy, trust input, index or linked worktree has changed
- **THEN** the next affected mutation is rejected with the precise coordinate
- **AND** already observed effects remain accurately reported

#### Scenario: Partial worktree synchronization recovers safely

- **WHEN** selected refs moved but one linked worktree could not synchronize
- **THEN** the result identifies completed and remaining effects
- **AND** recovery re-observes refs and worktrees before continuing
- **AND** unrelated content and refs remain unchanged

### Requirement: Control replacement preserves trusted prior verification

Control replacement SHALL read independent-verification policy from both exact
committed objects and retain the stricter mode during acceptance. Changed gate
identities SHALL remain review evidence, not implicit provider enrollment.
Applying a changed floor SHALL require explicit authorization, exact accepted
and candidate commits, current proof, fresh effect admission and CAS.

#### Scenario: Candidate cannot disable its required verifier

- **WHEN** a candidate replaces a required accepted verification policy with disabled
- **THEN** control replacement still requires evidence under the prior policy

#### Scenario: Executing authority is not an ordinary unverified change

- **WHEN** runtime selection, hook execution or Git-effect implementation changes
- **THEN** admission classifies the changed path as control and applies that policy

#### Scenario: Changed gate identities retain local-first acceptance

- **WHEN** both exact policies disable independent verification and gate execution changes
- **THEN** admission does not inspect or require host provider configuration
- **AND** the report exposes changed obligations without claiming semantic equivalence
- **AND** apply without explicit candidate selection is rejected without moving refs
- **AND** exact authorized acceptance remains reachable without an external receipt

#### Scenario: Uncommitted policy cannot change the verification requirement

- **WHEN** worktree policy differs from the selected candidate commit
- **THEN** verification selection uses the committed candidate and accepted predecessor

### Requirement: Review projection is distinct from accepted publication

Review publication SHALL project an exact trusted Git object without requiring
candidate checkout identity, completed Change proof or premature archive. It
SHALL enforce the shared target-role and introduced-range obligations and exact
peer-local CAS. Accepted/release targets SHALL retain repository proof and
closeout requirements. Proposal refs SHALL not become authoring lanes.

#### Scenario: An unfinished signed snapshot enters review

- **WHEN** an admitted selected object contains an unfinished official Change and targets proposal refs
- **THEN** publication and pre-push admit review without a fabricated proof
- **AND** each selected peer receives the same object while local accepted refs remain unchanged

#### Scenario: Review and accepted targets share a request

- **WHEN** a request includes both review and accepted or release targets
- **THEN** all selected target obligations are required before the first remote effect
- **AND** the review target cannot exempt another target from proof or closeout

#### Scenario: Invalid objects or ranges are offered for review

- **WHEN** the selected signature is untrusted or introduced commits violate declared policy
- **THEN** review publication is blocked before any peer update
- **AND** the report identifies object or range admission rather than missing product proof

### Requirement: Publication replay derives proof obligations from destinations

Publication replay SHALL derive applicable proof requirements from current exact
target obligations, not from a caller-controlled proof-selection label. Review
requests SHALL not fabricate Commitment or proof records. Required proof, source
trust, target policy and observed old OIDs SHALL be checked before each effect;
unavailable outcomes SHALL remain UNKNOWN rather than permission to repeat.

#### Scenario: Review receipt replays without a proof record

- **WHEN** the exact review request remains applicable and its object and peers are unchanged
- **THEN** replay applies or recognizes the existing effect without creating a product proof
- **AND** an already matching peer is not rewritten

#### Scenario: A receipt claims review semantics for a protected target

- **WHEN** a request's carried proof selection is weakened while its target requires accepted proof
- **THEN** replay rejects the request before the first update
- **AND** self-consistent request hashes do not substitute for current target admission

#### Scenario: Required facts change after the first peer succeeds

- **WHEN** source trust, selected proof, target policy or a pending peer ref changes between effects
- **THEN** the next peer is re-observed and freshly admitted before mutation or an already-applied claim
- **AND** confirmed earlier effects are retained while a blocked peer remains untouched
- **AND** partial and unavailable outcomes remain distinct from no effect or complete publication

### Requirement: Generation reclamation uses fresh operational facts

ETHOS SHALL reclaim only exact owned generations without current operational
dependencies. Every destructive step SHALL recheck dependency observations and
directory identity under the selected-runtime fence. Reclamation SHALL report
completed, retained and deferred resources independently from activation. A
listed path deleted while it is observed SHALL count as an observed absence,
not as an unknown observation.

#### Scenario: A consumer appears after initial observation

- **WHEN** a process, config or interpreter binding begins referencing a candidate before its deletion boundary
- **THEN** the fresh observation retains that generation
- **AND** selected and retained generation bytes remain unchanged.

#### Scenario: Historical observations accumulate

- **WHEN** repeated successful activations record paths of superseded runtimes
- **THEN** those historical records alone do not retain the runtimes
- **AND** reclamation neither deletes nor rewrites the historical records
- **AND** repeated cleanup converges without adding generation directories.

#### Scenario: Cleanup observation becomes unavailable

- **WHEN** runtime activation succeeds but a required consumer observation cannot be read
- **THEN** activation remains observable as successful and reclamation is deferred
- **AND** candidates without a completed fresh admission remain untouched
- **AND** the result reports the exact unavailable boundary and a public recovery action.

#### Scenario: A later cleanup step fails

- **WHEN** one generation is removed and a later observation or deletion fails
- **THEN** the report preserves the completed removal and identifies remaining paths
- **AND** retry derives fresh candidates rather than claiming rollback or repeating a vanished effect.

#### Scenario: Selector or candidate identity changes

- **WHEN** the selected runtime or exact candidate directory changes before its destructive effect
- **THEN** reclamation rejects the stale coordinate
- **AND** it does not delete a replacement directory under the old name.

#### Scenario: A listed path is deleted while it is observed

- **WHEN** another process deletes a path that the process listing names while reclamation is observing it
- **THEN** reclamation treats that path as absent and completes
- **AND** a dangling symbolic link that the listing names still defers reclamation
- **AND** a listed path that resolves into a generation still retains that generation.

### Requirement: OpenSpec active intent is visible across governed branch trees

ETHOS SHALL observe active official Changes in configured integration, accepted
and release Git trees. Active intent SHALL remain valid through source
integration and delivery. Each transition SHALL separately require exact source
and policy proof, current authority and its own CAS preconditions.

#### Scenario: active intent accompanies accepted source

- **WHEN** an accepted or release source tree contains a valid active Change
- **THEN** its presence is an ordinary observation, not an archive-required gap
- **AND** current source proof and effect admission remain required.

#### Scenario: another governed branch carries active intent

- **WHEN** the current checkout differs from a configured governed branch
- **THEN** its observed Change names remain visible with the exact branch role
- **AND** presence alone is neither a warning nor authority to mutate that branch.

#### Scenario: a required Git observation is unavailable

- **WHEN** ETHOS cannot read a required branch or source tree
- **THEN** the report preserves UNKNOWN and its precise missing fact
- **AND** it does not silently interpret failure as an empty Change list.

### Requirement: Repository transition proof binds source intent independently of archive

ETHOS SHALL admit repository-transition proof only for the exact source commit,
tree, official acceptance and required policy floor. Active and attested archived
intent SHALL use the same source-binding rule. Authoring Lease lifetime SHALL
not replace current effect authority or invalidate accepted source evidence.

#### Scenario: exact source carries unfinished delivery intent

- **WHEN** exact proof covers a valid active Change and the declared source floor
- **THEN** candidate-to-accepted admission may consume that proof before archive
- **AND** it does not assert completed delivery or authorize a later effect.

#### Scenario: carried acceptance differs from source

- **WHEN** proof names the correct commit but carries different acceptance
- **THEN** repository-transition admission rejects the intent binding
- **AND** green check results cannot compensate for that mismatch.

#### Scenario: the authoring Lease has retired

- **WHEN** source proof remains exact and applicable after its Work Lane retires
- **THEN** an independently authorized repository transition can consume it
- **AND** current-lane authoring still requires its own live Lease.

### Requirement: Gate representation preserves common governance

ETHOS SHALL evaluate applicable binding, OpenSpec, commit and declared release
obligations independently of inline or registry gate storage. Product-specific
conformance SHALL use explicit provider composition while retaining the trusted
predecessor verification floor during control replacement.

#### Scenario: Equivalent adopter gate declarations

- **WHEN** two otherwise equivalent adopters store the same gates inline or in a registry
- **THEN** common governance and relevant effect admission yield equivalent outcomes
- **AND** neither requires ETHOS product documents or package metadata by implication.

#### Scenario: Real OpenSpec observation fails

- **WHEN** an enabled adopter OpenSpec configuration is invalid
- **THEN** public audit reports the actual required gap
- **AND** no capability boolean replaces that observation with a passing result.

#### Scenario: Candidate removes predecessor product verification

- **WHEN** a candidate disables a verification obligation required by its accepted predecessor
- **THEN** its control-replacement acceptance still requires the predecessor obligation
- **AND** candidate gate storage or profile naming cannot waive it.

### Requirement: Declared release roles share one validation owner

ETHOS SHALL validate present release-role declarations against configured branch
roles through one semantic owner. Missing optional declarations impose no release
constraint. Malformed present declarations fail closed. Branch membership is
order-independent; duplicate or incorrectly typed entries are invalid.

#### Scenario: Contradictory protected branch declarations

- **WHEN** declared protected branches omit or add a branch relative to effective protected roles
- **THEN** common audit and relevant integration admission reject with a precise policy gap
- **AND** the attempted integration leaves its destination ref unchanged.

#### Scenario: Equivalent branch order

- **WHEN** a declaration contains each effective protected branch exactly once in a different order
- **THEN** its role-consistency check passes.

#### Scenario: Absent optional release declaration

- **WHEN** an adopter does not declare release configuration
- **THEN** common governance imposes no product release files, tag convention or attestation format.

#### Scenario: Malformed present declaration

- **WHEN** present release configuration is unreadable, malformed or has invalid protected-ref fields
- **THEN** the owning report identifies the invalid declaration
- **AND** no consumer silently converts it to absent policy.

### Requirement: Runtime binding reports selected schema provenance

ETHOS SHALL derive schema provenance from the actual runner schema owner and
runtime admission from the selected execution authority. Correctly bound package
execution SHALL NOT require schemas in the adopter checkout. Profile validity or
gate representation alone SHALL NOT grant mutation authority.

#### Scenario: Registry adopter uses its selected package runtime

- **WHEN** a registry adopter invokes its current immutable package runtime
- **THEN** prewrite admits a valid otherwise-authorized write
- **AND** diagnostics identify the package schema origin without claiming local schemas.

#### Scenario: Unrelated adopter schema path

- **WHEN** an adopter contains a file whose name resembles an ETHOS schema
- **THEN** that file does not change the reported or selected runner schema source.

#### Scenario: Stale execution authority

- **WHEN** a tracked mutation invokes a stale or foreign execution authority
- **THEN** admission rejects under the existing currentness boundary
- **AND** supplies recovery derived from the current target and selected runtime.

### Requirement: Publication composes historical repair with forward integration

ETHOS SHALL recognize an original peer object through an unambiguous chain of
completed native history repairs, each conserving exact payloads, ordered parents
and trusted signatures under its recorded source policy. Only refs named
throughout the chain SHALL inherit repaired publication provenance. The peer's
advertised object SHALL remain the CAS precondition, and the last verified
replacement tip SHALL own forward commit-range validation.

#### Scenario: Repaired provenance does not substitute for current admission

- **WHEN** a ref inherits repaired publication provenance
- **THEN** current proof, accepted effect, candidate equality and protected
  publication admission are still each required independently

#### Scenario: Signed forward commits follow a verified replacement

- **WHEN** the peer ref holds the recorded repair source and proposed accepted
  descends from its verified replacement
- **THEN** publication recognizes the historical segment as repaired
- **AND THEN** the common range owner checks replacement-to-proposed commits
  without scanning the repaired historical segment as new integration.

#### Scenario: Peer holds an earlier mapped original commit

- **WHEN** the protected peer ref holds an exact original commit in the
  completed repair mapping and the repair replaced that same local ref
- **THEN** pre-push and publication readiness use the verified replacement
  tip as the forward-validation baseline
- **AND THEN** the peer's advertised old OID remains the exact CAS precondition
  rather than being substituted with the mapped or replacement OID.

#### Scenario: A forward commit violates policy

- **WHEN** a descendant after the verified replacement has an invalid subject,
  identity or required signature
- **THEN** range admission rejects that descendant despite valid repair
  provenance.

#### Scenario: Repair provenance does not establish the requested relationship

- **WHEN** the target ref is not in the repair, the peer's old OID is not a
  mapping key, replacement ancestry is absent, or repair evidence is missing,
  invalid or ambiguous
- **THEN** the request is not admitted as a repaired-history publication
- **AND THEN** no remote or local ref is changed by the observation.

#### Scenario: Accepted publication consumes the verified forward baseline

- **WHEN** public pre-push or publication evaluates accepted descendants after
  a verified repair of the peer's exact old object or mapped historical prefix
- **THEN** the accepted topology check evaluates forward ancestry from the
  verified replacement while still requiring the current candidate head
- **AND THEN** proposed-object proof and its accepted effect remain required
- **AND THEN** each peer applies only its observed old-to-proposed ref
  transaction.

#### Scenario: Repaired ancestry cannot excuse missing current acceptance

- **WHEN** the repair relation is valid but current proof, accepted effect or
  candidate equality is absent
- **THEN** publication is rejected without changing either peer.

#### Scenario: An original prefix survives a subsequent repair

- **WHEN** a verified replacement enters a later repair's exact source history
  and that completed repair replaces its object before current forward work
- **THEN** original-object provenance composes both native mappings
- **AND THEN** commit-range admission checks only last-tip descendants, retaining
  every repair witness and the peer's original CAS object
- **AND THEN** an invalid forward subject or signature still rejects publication.

#### Scenario: A predecessor or ref relationship is absent

- **WHEN** any necessary completed repair is missing or invalid, multiple paths
  establish the relation, or a ref is absent from a necessary repair effect
- **THEN** that repaired-history relationship is not admitted
- **AND THEN** no local or remote ref changes during observation.

### Requirement: Native hook decisions preserve JSON evidence

ETHOS SHALL emit a JSON-native rejection for failed native Git hook admission,
preserving valid nested immutable evidence, required gaps and continuation.
Invalid evidence values SHALL produce a stable blocked transport result rather
than a traceback or fabricated success. Successful native hooks SHALL retain
quiet zero-exit behavior.

#### Scenario: Rejected report contains immutable proof values

- **WHEN** pre-push rejects or cannot determine admission and carries nested
  immutable Attestation or Commitment mappings and ordered collections
- **THEN** stderr contains one valid JSON report with the original verdict,
  required gaps, evidence and next action
- **AND** the original immutable values remain unchanged

#### Scenario: Evidence cannot be represented as JSON

- **WHEN** a failed hook report contains unsupported or nonfinite values
- **THEN** the hook exits nonzero with `hook_report_not_json_native` JSON
- **AND** no Python traceback replaces the machine-readable result

#### Scenario: A notification needs no admission

- **WHEN** Git reports an irrelevant or completed notification
- **THEN** the hook does not initialize policy or CLI machinery for serialization

### Requirement: Lane intent respects its native contribution boundary

ETHOS SHALL resolve a Work Lane's current official intent within its native
creation and contribution history. A merge inherited before lane creation SHALL
NOT displace a different active Change. Existing effect records provide that
boundary without extending Lease or introducing another intent carrier.

#### Scenario: New lane inherits an archived predecessor and active work

- **WHEN** an accepted tree contains an archived predecessor and a different
  active Change, and a new owned lane starts at that tree
- **THEN** prewrite and default planning select the active Change
- **AND** the predecessor archive does not authorize or block the active files

#### Scenario: Same lane archives its own contribution

- **WHEN** a lane merges incoming active intent and then archives its own Change
- **THEN** its closeout retains the archived contribution's identity
- **AND** it does not silently take ownership of the incoming Change

#### Scenario: An explicit selection is carried through proof

- **WHEN** plan or prove explicitly selects a present official Change
- **THEN** its accepted intent, execution plan and proof carry that same identity
- **AND** new proof binds the current lane and Lease generation
- **AND** an archived predecessor's proof cannot substitute for that selection

#### Scenario: Contribution provenance is ambiguous or corrupt

- **WHEN** competing creation or contribution facts cannot establish the selected
  lane boundary, or selected effect evidence is invalid
- **THEN** the observation reports a precise unresolved provenance gap
- **AND** it does not guess from task counts or unrelated archived intent

### Requirement: Exact accepted proposal retirement

ETHOS SHALL retire a proposal through its existing publication effect only after
fresh observations establish closed review, exact peer ref identity, and that its
exact tip stays preserved: by accepted absorption, by an owned Work Lane that
reaches it, or by the same peer's ref for its closed review. A candidate ref
SHALL NOT retain a proposal. Retirement SHALL NOT depend on main release
convergence, active Change presence, or a historical authoring Lease.

#### Scenario: Accepted contribution no longer needs its review projection

- **WHEN** a proposal tip is reachable from local accepted dev and the selected
  peer's accepted dev, and no matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** a delayed main release does not block retirement

#### Scenario: A retained projection is redundant

- **WHEN** an unabsorbed proposal tip is reachable from an owned Work Lane, or
  the same peer names it at the ref of a closed review of that branch, and no
  matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** the report names the retainer that keeps the tip retrievable

#### Scenario: Incomplete or unrelated evidence cannot authorize deletion

- **WHEN** neither absorption nor a retainer is observed, a review is open, the
  peer tip changed, or a required observation is unavailable
- **THEN** retirement preserves the proposal and reports the owning boundary
- **AND** patch equivalence, a user-supplied closed flag, unrelated review
  results, and a candidate ref that landing resets cannot substitute for the
  required observations

#### Scenario: Replayed deletion converges without repeated effects

- **WHEN** one peer was retired before interruption and another remains pending
- **THEN** recovery reobserves the same exact plan and skips the absent peer
- **AND** remaining peers are independently readmitted before deletion

#### Scenario: Verified history repair preserves accepted contribution identity

- **WHEN** an immutable, completed ETHOS history-repair effect establishes one
  exact old proposal tip to replacement mapping, and the replacement is absorbed
  by local and peer accepted dev
- **THEN** retirement recognizes that verified relationship without restoring
  the old history
- **AND** missing, ambiguous or invalid repair evidence cannot authorize deletion

#### Scenario: Publication retains its original positive-object guarantees

- **WHEN** the existing publication command projects commits or annotated tags
- **THEN** target updates still match the exact trusted source object
- **AND** retirement mode cannot delete protected, candidate, or tag resources

#### Scenario: Verified native refresh preserves the accepted contribution

- **GIVEN** validated native refresh evidence binds the old contribution, candidate
  and refreshed output, and the proposal is contained in the old input history
- **WHEN** isolated native composition reproduces the exact output tree and the
  output is absorbed by local and peer accepted dev
- **THEN** public retirement consumes that relationship without recreating an
  active historical Change, Lease or old branch
- **AND** current closed-review, exact peer identity and fresh CAS checks still apply
- **AND** missing, invalid, ambiguous or nonconserving evidence does not authorize
  deletion, while unavailable required observations remain explicit

#### Scenario: Remote retirement exposes separately admitted local closure

- **WHEN** selected peer retirement has completed but a same-named local proposal remains
- **THEN** the result preserves confirmed remote effects and reports `retirement_pending`
- **AND** its continuation invokes the native local retirement owner with exact root and OIDs
- **AND** the publication receipt does not authorize that local mutation
- **AND** replay reports full retirement only after the requested local projections are absent

#### Scenario: Local retirement shares verified accepted-contribution meaning

- **WHEN** a local proposal is accepted by ancestry, verified signature repair or conserved native refresh
- **THEN** its native retirement and compensation consume the same contribution observer as publication
- **AND** topic role, current accepted OID, no linked worktree, no Lease and exact CAS still apply
- **AND** missing, invalid or nonconserving evidence blocks deletion; unavailable conservation remains UNKNOWN
- **AND** failed local effect evidence preserves or compensates the exact original ref

### Requirement: Independent release selection preserves accepted source

ETHOS SHALL expose proof-bound promotion of exact current accepted source to the
declared independent release ref through existing land and Git effect owners.
Fresh source and prior release coordinates, accepted effect, repository-transition
proof and local coordination SHALL remain independent preconditions.

#### Scenario: Accepted source is selected for release

- **WHEN** an authorized request names current accepted and prior release objects
- **THEN** one native CAS advances release without rewriting source
- **AND** the transaction asserts the accepted ref
- **AND** dirty linked release content causes rejection before the effect

#### Scenario: Release movement lacks authority

- **WHEN** source differs from accepted or proof, accepted effect or executor
  intent is missing or stale
- **THEN** release admission rejects without a partial ref update

### Requirement: Release tags preserve native product version authority

ETHOS SHALL create requested signed annotated tags from exact committed native
version authority through the existing Git effect. Independent release may
advance its declared branch; an accepted mirror SHALL already be aligned and
remain an assertion. Malformed, conflicting or untrusted inputs SHALL block.
An existing package version SHALL NOT require a parallel VERSION carrier.

#### Scenario: Native package version owns release

- **WHEN** package.json is the unambiguous committed version owner
- **THEN** the tag matches that version and peels to accepted
- **AND** its signature passes current protected trust verification
- **AND** release changes and the new tag use one native transaction

#### Scenario: Tag or version conflicts

- **WHEN** the requested tag disagrees with version, already exists without a carried
  request, is divergent or lacks a trusted signature
- **THEN** neither release nor tag ref changes

#### Scenario: Accepted mirror creates a release tag

- **WHEN** accepted closeout has aligned the protected branches and the request
  names that exact accepted object for both coordinates
- **THEN** the release owner creates the tag while asserting both branch objects
- **AND** a misaligned mirror is directed to accepted closeout without effects
- **AND** a release-tag hook lacking executor intent selects the exact release preview

#### Scenario: Aligned release has no requested change

- **WHEN** the exact release branch already equals accepted and no tag is requested
- **THEN** validation succeeds without a ref update or new effect Attestation

#### Scenario: Interrupted or repeated release

- **WHEN** release resumes after an observed or unknown effect in either mirror mode
- **THEN** ETHOS observes exact refs and evidence before replay
- **AND** an accepted tag object is reused without resigning
- **AND** compensation reverses only changed refs and retains branch assertions
- **AND** pending linked worktree synchronization remains explicit

### Requirement: Accepted delivery is not another contribution integration

ETHOS SHALL distinguish shipping exact verified accepted content from introducing
new contributions. Only the former may reuse accepted effect and current proof.
Reuse SHALL NOT assert signatures or later-policy compliance for pre-adoption
history. Accepted content is the current accepted commit or, for an existing
release tag object, the commit at which an attested ETHOS release effect
created that object while that commit remains in accepted history.

#### Scenario: Accepted source contains pre-adoption history

- **WHEN** accepted source with valid effect and proof is selected for main or tag
- **THEN** publication preserves history without rescanning accepted ancestors as
  new contributions
- **AND** exact source, tag signature, target policy and peer CAS remain required

#### Scenario: Content was not accepted

- **WHEN** proposed source is neither current accepted nor the attested release
  commit of the exact tag object in accepted history, or its evidence fails
- **THEN** reuse grants no admission
- **AND** normal introduced-range subject and signature checks remain enforced

### Requirement: Historical effect identity survives profile schema evolution

ETHOS SHALL validate repair and Git-ref-effect Attestations, and the accepted
pre-state revisions of a current Git effect, including the unedited accepted
checkout a closeout advances, against each exact former commit's stable
repository identity, not today's schema. Missing, malformed or mismatched
historical identity SHALL block without current-profile or caller fallback.
Current effects SHALL still require the strict current profile in every other
checkout and every revision they produce.

#### Scenario: Retired profile field does not erase a valid repair

- **GIVEN** a completed exact repair of a former accepted commit whose profile
  declares the same repository ID and a field removed from the current schema
- **WHEN** publication checks a declared peer still holding an original commit
  covered by that repair
- **THEN** provenance validation uses the former commit's stable identity
- **AND THEN** the old field alone does not block the repaired-history relation
- **AND THEN** current proof, target policy and remote CAS remain independent
  conditions before any effect.

#### Scenario: Accepted closeout remains verifiable after profile cleanup

- **GIVEN** a completed candidate-to-accepted effect whose former commit has
  the same repository ID but a field later removed from the profile schema
- **WHEN** publication revalidates the accepted effect at the new source HEAD
- **THEN** its recorded Git effect remains verifiable against the former
  commit's stable repository identity
- **AND THEN** it does not report the accepted closeout as unattested solely
  because the former profile has an obsolete field.

#### Scenario: An adopter lands its profile migration across a retired schema

- **GIVEN** an adopter whose accepted candidate head and unedited accepted
  checkout declare the same repository ID with formats removed from the current
  profile schema
- **WHEN** its Work Lane lands a candidate that migrates the profile to the
  current schema and closeout advances the accepted checkout to it
- **THEN** each Git effect reads that accepted pre-state through its stable
  historical identity
- **AND THEN** control replacement keeps the predecessor's committed
  verification mode, requires it when unreadable, and binds the exact candidate
- **AND THEN** the produced candidate revision is validated against the current
  schema
- **AND THEN** an edited accepted checkout, a changed repository ID, an invalid
  produced profile and the trust, ref role, CAS, proof and lease refusals still
  block.

#### Scenario: Historical identity cannot be guessed

- **WHEN** the former profile is absent, unreadable, syntactically malformed,
  declares no nonempty repository ID, or declares a different repository ID
- **THEN** historical repair or effect provenance is rejected before publication
- **AND THEN** the current profile, receipt text or peer name does not replace
  the former commit's identity.

#### Scenario: Other repair bindings remain mandatory

- **WHEN** the historical identity matches but the recorded policy or commit
  payload digest, signed replacement relation, effect Attestation or current
  source proof is invalid
- **THEN** the corresponding existing admission blocks publication
- **AND THEN** no peer ref changes.

#### Scenario: Current profile remains strict

- **WHEN** the current checkout's profile violates the current typed schema
- **THEN** status, planning, proof and publication remain blocked
- **AND THEN** historical identity tolerance cannot validate the current
  operational profile.

### Requirement: Explicit peer-scoped publication

For exact `ethos publish --ref`, callers MAY explicitly select a nonempty
subset of declared peers by ID for that invocation. Omitted selection SHALL
retain the all-peer request; peer health SHALL never select implicitly. ETHOS
SHALL validate the full declared topology, then observe only selected peers
and compile one immutable request binding each selected ID, Git remote, ref,
and exact expected and desired OIDs.

#### Scenario: One declared peer is unavailable

- **GIVEN** GitLab and GitHub are declared and GitLab cannot be observed
- **WHEN** the caller selects only GitHub for an exact publication request
- **THEN** ETHOS may admit and apply the GitHub peer-local transaction without
  observing or mutating GitLab
- **AND THEN** the result identifies GitLab as declared but unselected, not
  published.

#### Scenario: No peer is explicitly selected

- **WHEN** one declared peer is unavailable and the caller supplies no `--peer`
- **THEN** the all-peer request remains unproved and no peer effect begins
- **AND THEN** ETHOS does not silently substitute an available subset.

#### Scenario: Selector is unknown or repeated

- **WHEN** a caller names an undeclared peer ID or repeats one ID
- **THEN** ETHOS rejects the request before remote observation or mutation.

### Requirement: Peer-scoped replay and reporting remain bounded

Before and between remote effects, replay SHALL recheck each selected
ID-to-remote binding and the existing source, proof, ref-role, signature and
exact-CAS obligations. A receipt SHALL NOT accept a new selector or widen its
bound peer set. Results and Attestations SHALL name selected and unselected
peers, and SHALL NOT claim an unselected peer was published.

#### Scenario: Bound peer identity changes before replay

- **WHEN** a receipt's selected peer ID no longer maps to its bound Git remote
- **THEN** replay rejects the receipt before any remote push
- **AND THEN** another declared peer or remote cannot inherit that receipt.

#### Scenario: An existing receipt is given a new selector

- **WHEN** a caller combines `--receipt` with `--peer`
- **THEN** ETHOS rejects the ambiguous request without changing its targets.

#### Scenario: The selected peer itself is unavailable

- **WHEN** the selected peer cannot be observed before an exact-CAS effect
- **THEN** ETHOS reports that selected peer's missing fact and performs no push
- **AND THEN** its continuation preserves the explicit peer selection rather
  than falling back to another peer.

#### Scenario: Release and review roles keep their proof boundaries

- **WHEN** a caller selects one peer for an accepted branch, release branch,
  signed annotated release tag, or proposal ref
- **THEN** the existing role-specific source, signature and proof obligations
  still apply to that selected effect.

### Requirement: Attested archive admits bounded authored reference repair

After an official archive, ETHOS SHALL derive repair scope for a tracked Markdown
document only when its parsed local destination still names an artifact moved by
that exact attested archive. The current Git tree, runtime, actor, Lease and
postimage admission remain required. Repair SHALL NOT replay archive, silently
rewrite authored prose or create another tracked intent authority.

#### Scenario: A current document retains a navigable active-Change link

- **GIVEN** an exact archive effect is attested and its archived target exists
- **AND** a tracked authored Markdown document still links to the removed active artifact
- **WHEN** its owner requests exact-path prewrite or stages a reviewed repair
- **THEN** prewrite and the native commit hook admit only that document
- **AND** ordinary patch, source freshness and repository quality checks still apply
- **AND** the repair scope disappears when the stale link leaves the committed tree

#### Scenario: A mention does not establish a repair relation

- **WHEN** the requested file contains only code-fenced text, an unrelated path or no parsed link to the moved artifact
- **THEN** the archive grants no write scope to that file
- **AND** a missing target, unsupported reference or absent archive Attestation remains blocked

### Requirement: Proof execution carrier is not proof authority

An exact-head repository proof MAY run gates in a separately selected clean
worktree. The authoring Work Lane SHALL remain the authority for actor, Lease,
committed intent and proof issuance. The execution carrier SHALL use the same
Git common directory, be detached at that exact commit and have an unchanged
index and tracked/untracked source corresponding to its HEAD.

#### Scenario: A staged archive needs a current-policy proof

- **WHEN** a Work Lane has a reviewed official archive staged and its unchanged
  HEAD requires new quality checks
- **AND** the caller selects a clean, same-common-dir carrier at that HEAD
- **THEN** ETHOS executes the current required checks against the carrier
- **AND** a passing Attestation binds the original lane's intent, HEAD and Lease
- **AND** the original staged and working bytes remain unchanged.

#### Scenario: The carrier is not the exact committed source

- **WHEN** the selected carrier is foreign, attached to another branch, dirty,
  at another commit, or changes during execution
- **THEN** ETHOS rejects or reports an unknown outcome without a passing proof
- **AND** it neither edits the authoring lane nor treats the carrier's Lease as
  permission.

#### Scenario: The requested exact HEAD is stale

- **WHEN** `--expect-head` differs from the authoring lane's current HEAD
- **THEN** ETHOS rejects before executing carrier gates
- **AND** it preserves the original staged archive and issues no proof.

### Requirement: Carrier proof preserves independent admission boundaries

The proof policy SHALL be selected from the committed source and evaluated at
the current required floor. Earlier policy results, carrier cleanliness,
repository identity, valid Lease and successful checks are independent claims;
none substitutes for another. The ordinary clean-lane proof path SHALL not
require an execution carrier.

#### Scenario: Authority or staged content changes during checks

- **WHEN** the authoring lane's HEAD, Lease generation, staged index or working
  content changes before issuance
- **THEN** ETHOS does not mint a passing Attestation from completed gates
- **AND** it preserves the exact completed-check diagnostics for recovery.

#### Scenario: Historical proof cannot meet a stronger current floor

- **WHEN** previous check materials do not prove each currently required
  quality subject
- **THEN** ETHOS requires execution of the missing current checks
- **AND** it does not re-sign the historical proof or weaken the policy.

### Requirement: Blocking Canonical Guidance Has a Repair Path

ETHOS SHALL admit corrective prewrite for an existing canonical OpenSpec spec
named by a current, valid official spec INFO finding. The source SHALL be the
selected active Change or a verified archive effect that owns that output.
Multiple findings for one spec SHALL map to one path. Admission SHALL retain
the actor, Lease, runtime, exact path and source bindings; it SHALL NOT satisfy
ordinary proof or commit admission.

#### Scenario: Exact canonical repair is reachable

- **WHEN** official validation reports a valid canonical spec with blocking INFO and the owning coordinated Work Lane requests prewrite for that exact spec file
- **THEN** ETHOS admits only that file for correction
- **AND THEN** ordinary proof remains blocked until fresh validation clears the finding.

#### Scenario: Archived Change repairs multiple findings in one output

- **WHEN** a verified native archive effect names the canonical spec, official validation reports two valid INFO findings in it, and the same coordinated Work Lane requests prewrite for that file
- **THEN** ETHOS admits that one exact path without recreating the active Change
- **AND THEN** ordinary status and proof remain blocked until fresh validation clears both findings.

#### Scenario: Unrelated or unsupported paths gain no authority

- **WHEN** the request includes an unrelated path, a missing or symlinked spec, a mismatched finding, invalid validation evidence, or a missing, mismatched or unverified archive effect
- **THEN** the finding grants no corrective prewrite for the unsupported path.

#### Scenario: Blocked status selects a repair action

- **WHEN** canonical INFO is the blocking gap for a coordinated Work Lane with an active Change or verified archived output
- **THEN** status names prewrite for one exact affected canonical spec instead of another status observation.

### Requirement: Native pre-push validates release-tag objects

ETHOS native pre-push SHALL validate the actual object supplied for a declared
release-tag ref as a trusted signed annotated tag with exact declared name and
committed product version at its release commit: the current accepted commit,
or an earlier accepted commit where an attested release effect created exactly
this tag object. A signed peeled commit alone SHALL NOT satisfy tag admission.
A divergent remote tag SHALL NOT be replaced, and exact remote publication
SHALL reach the same decision.

#### Scenario: Plain commit is offered as a release tag

- **WHEN** Git supplies a commit OID as the new value of a declared
  `refs/tags/vX.Y.Z` update
- **THEN** native pre-push exits nonzero with a tag-object gap
- **AND THEN** passing commit proof does not authorize the update.

#### Scenario: Signed tag is published or already current

- **WHEN** Git supplies a trusted signed annotated tag matching the exact ref
  name, committed version and current accepted commit
- **THEN** native pre-push can admit creation while the remote tag is absent,
  or an identical remote no-op
- **AND THEN** it retains current proof, accepted effect and ref-role checks.

#### Scenario: A peer that missed the release receives it later

- **WHEN** accepted history has advanced past a release commit and a declared
  peer lacks the exact tag object the attested release effect created there
- **THEN** native pre-push and exact publication can admit that object for the
  selected peer, or an identical remote no-op
- **AND THEN** tag trust, name, version, proof and accepted effect are checked
  for the release commit and the publication effect is attested.

#### Scenario: Tag object or remote state is invalid

- **WHEN** the tag is lightweight, unsigned, untrusted, mismatched by name or
  version, neither at the current accepted commit nor the attested object of a
  release still in accepted history, or replaces a different remote tag object
- **THEN** native pre-push blocks without a remote effect.

### Requirement: Current-policy proof coexists with immutable superseded proofs

ETHOS SHALL select same-HEAD proofs only when their complete plan and evidence
match the current canonical policy, source intent, repository identity and
required floor. An internally valid superseded-policy proof SHALL remain
immutable history; it SHALL neither satisfy the current query nor veto a
separate valid current proof. Invalid envelope, artifact or statement bindings
and conflicting applicable proofs SHALL still fail closed.

#### Scenario: Current proof follows a policy upgrade

- **GIVEN** one exact commit has an internally valid proof under an earlier
  policy and another under the current canonical policy
- **WHEN** a repository transition selects proof for that commit
- **THEN** the current-policy proof may be admitted without deleting or
  rewriting the old record
- **AND THEN** the selected proof still binds the exact source, current intent
  and required floor.

#### Scenario: Only an old policy proof remains

- **WHEN** an exact commit has no proof matching the current canonical policy
- **THEN** proof admission reports the policy mismatch and blocks the
  transition.

#### Scenario: Caller selects an old record explicitly

- **WHEN** a caller selects an internally valid old-policy Attestation ID
- **THEN** ETHOS rejects that selection as insufficient current proof
- **AND THEN** it does not silently substitute a different record.

#### Scenario: Malformed or conflicting evidence remains blocking

- **WHEN** any current same-HEAD record has a broken envelope, artifact or
  statement binding, or applicable current-policy records conflict
- **THEN** a separate valid current proof does not hide that defect
- **AND THEN** no publication or accepted-ref effect is admitted from the set.

### Requirement: Native accepted-ref admission agrees with transition proof

The accepted-ref hook SHALL use the repository-transition proof selector used
by promotion preflight. Complete same-HEAD executions with the same accepted
intent, current policy, verifier and claim MAY differ in their execution facts,
plan and effect without blocking that transition. Candidate ancestry, exact
prepared ref intent and Git CAS remain independent requirements. Ordinary
full-binding proof queries SHALL retain their stricter conflict behavior.

#### Scenario: Two valid executions precede one accepted transition

- **GIVEN** two current proofs share the accepted assertion and policy but have
  different execution facts, plans and effects
- **WHEN** the authorized accepted-ref update reaches the native Git hook
- **THEN** the hook admits the same proof set as promotion preflight
- **AND THEN** the exact ref update succeeds only with its prepared intent.

#### Scenario: Different assertions remain contradictory

- **WHEN** the same HEAD carries proofs with different verifier or claim
- **THEN** accepted-ref admission blocks their contradiction
- **AND THEN** an ordinary full-binding query also remains strict.

### Requirement: Publication push budget covers native pre-push admission

When `ethos publish` applies an exact peer transaction, the push deadline SHALL
be a fixed transfer allowance plus twice the admission measured for that peer
immediately before the push. The repository's native pre-push hook re-derives
that admission, so a fixed constant alone SHALL NOT bound it.

#### Scenario: Range-dependent hook admission

- **WHEN** the admission of a peer transaction takes longer than the transfer
  allowance
- **THEN** the push deadline still covers the transfer allowance plus twice
  that measured admission
- **AND** a push that exceeds the derived deadline is reported as an unknown
  outcome and reobserved, exactly as before.

### Requirement: Unclassified ref moves fail with an explicit reason

ETHOS SHALL reject a candidate-integration ref move whose ref matches no declared branch role with `ref_transition_operation_unresolved:<ref>`, and SHALL leave that ref unmoved.

#### Scenario: A candidate integration targets an undeclared ref

- **WHEN** a landing integrates a proven Work Lane into a candidate branch that matches no resolved role
- **THEN** the candidate update fails with `ref_transition_operation_unresolved` naming that ref
- **AND** the candidate branch does not move

### Requirement: Attestation lifetimes end with the transition that consumes them

Every Attestation SHALL have exactly one lifetime derived from its predicate and existing bindings:
operation, head, lineage, window or open-predicate. A lifetime SHALL end only on positive evidence
that the set update observes, never on the absence of a branch or ref alone.

#### Scenario: A Work Lane is retired or its branch is absent

- **WHEN** a lane's retirement effect is selected or its branch is missing
- **THEN** its operation members remain while proof admission can resolve archived intent or
  proposal retirement can resolve refresh provenance through them
- **AND** they end together at the first set update that observes that the lane's branch is absent
  and no commit its ref updates name is reachable from a selected commit or a present pre-repair
  object

#### Scenario: A reader of a retired lane's records cannot be observed

- **WHEN** an update cannot observe whether proof admission or proposal retirement still selects a
  retired lane's records
- **THEN** those records remain and the update reports the gap

#### Scenario: An accepted head is superseded

- **WHEN** closeout advances the accepted ref from one commit to a later one
- **THEN** the proof, integration and publication records of the earlier commit end once no local
  ref, fully peeled tag, worktree HEAD or declared peer's last publication selects it
- **AND** its acceptance record remains as provenance for historical maintenance bases
- **AND** the current head's proof, acceptance and publication records remain

#### Scenario: Maintenance starts from a historical accepted base

- **WHEN** a native maintenance lane selects an earlier accepted base after the current train
  advances
- **THEN** its original accepted-effect record remains selectable and fully validated
- **AND** the new source still requires current proof, signatures, actor and Lease admission
- **AND** retaining provenance does not restore an expired proof or authorize an effect

#### Scenario: A release tag or repair lineage still exists

- **WHEN** a release tag exists, or a governed ref or a declared peer still reaches a pre-repair
  object
- **THEN** its release or repair record remains
- **AND** the record of a kept runtime generation and the starter formation also remain

#### Scenario: A tag or runtime package is no longer observed

- **WHEN** a release tag or a runtime package is missing locally
- **THEN** the release record and every accepted release identity remain
- **AND** a repair record ends only once every pre-repair object it names is absent locally

#### Scenario: Lifetime facts cannot be observed

- **WHEN** an update cannot observe refs, worktrees or pre-repair objects
- **THEN** it removes no member and reports the gap

#### Scenario: A validity window passes

- **WHEN** a member's `valid_until` has passed
- **THEN** the next set update removes it

#### Scenario: A predicate has no product reader

- **WHEN** a member's predicate has no product lifetime
- **THEN** the member remains until an admitted release removes it

#### Scenario: A needed member has ended

- **WHEN** a transition requires a member that has left the set
- **THEN** the transition fails closed with its existing missing-evidence gap
- **AND** it does not infer the absent member

### Requirement: Archive completion requires exact postimage quality

Archive completion SHALL require native OpenSpec validity and the existing
applicable proof for the actual resulting HEAD. Prearchive proof and Git effect
evidence SHALL NOT establish postimage quality. Pending verification SHALL
preserve and report the observed committed effect without claiming completion.

#### Scenario: Native postimage finding before Git CAS

- **WHEN** official archive projection would leave a canonical spec invalid or
  with a blocking native finding
- **THEN** ETHOS validates that actual uncommitted postimage before creating a
  commit or updating the lane ref
- **AND** it compensates its own archive mutation and reports a source delta
  repair path only when the native finding maps to that changed spec; otherwise
  it requires further resolution instead of retrying the unchanged archive
- **AND** an already staged caller-owned archive remains visible as retained
  mutation, not a falsely absent effect or permission to discard its bytes
- **AND** a valid authored Purpose or corrected requirement remains able to
  archive through the normal postimage proof boundary

#### Scenario: Archive changes an input consumed by a repository check

- **WHEN** prearchive proof passes but the resulting source has no passing applicable proof
- **THEN** archive reports a blocked committed repair boundary with the actual HEAD
- **AND** its continuation selects that HEAD's existing proof command and repository root
- **AND** the reported native command comes from the committed archive artifact,
  retaining `skip_specs` rather than reading a now-absent active Change
- **AND** stale, failed or unrelated proof cannot make archive completion pass

#### Scenario: Exact postimage proof is available

- **WHEN** native OpenSpec validity and exact postimage proof both pass
- **THEN** archive completion passes using the original effect evidence
- **AND** replay neither repeats Git effects nor reruns checks

#### Scenario: Final task completion accompanies the official archive

- **GIVEN** the selected source HEAD has its separately admitted review evidence
- **WHEN** the staged official archive only advances the top-level OpenSpec task checkboxes from open to complete
- **THEN** archive admission preserves the unchanged task descriptions and other source artifacts
- **AND** it recognizes the completed postimage without requiring a new prearchive source commit and repeated review CI
- **AND** unchanged or partly open tasks, changed task prose, or another content edit remains blocked with an exact cause
- **AND** the checkbox does not replace postimage validation, proof, or evidence of the external review

### Requirement: Current prose preserves meaning without copied execution state

ETHOS SHALL keep obligations, dependency order, task progress and observed
results at their existing semantic owners. Current entrypoints SHALL expose the
relevant route without requiring historical narratives. Reducing text or token
cost SHALL NOT remove valid constraints, functionality, performance or acceptance.

#### Scenario: Completed observations leave the current plan entry

- **WHEN** historical execution detail is removed from a current entrypoint
- **THEN** exact source bytes remain recoverable through the existing history owner
- **AND** every still-valid obligation remains in its current owner or explicitly open
- **AND** task status and dated results are referenced rather than copied into another ledger

#### Scenario: A reader needs the next useful action

- **WHEN** a person or agent reads the current convergence entry
- **THEN** it reaches the existing task and authority owners without loading historical results
- **AND** local, installed, hosted and actual-use claims remain distinct
- **AND** measured text or token reduction alone does not prove semantic preservation

#### Scenario: Completed Change history leaves the current tree

- **WHEN** a completed OpenSpec archive has no remaining current-tree proof or reader consumer
- **THEN** current behavior is read from canonical specs, not that archive
- **AND** a reviewed deletion may retire its current-tree copy only after every byte remains reachable and recoverable from an exact Git revision
- **AND** incoming references are moved to the current owner or exact history retrieval
- **AND** an in-flight archive or unknown recovery path remains preserved
- **AND** calendar age alone grants no deletion authority

### Requirement: Accepted feedback closes through demonstrated improvement

ETHOS SHALL preserve each accepted feedback obligation's declared source scope,
responsible owner and acceptance conditions in official OpenSpec. Closure SHALL
require a demonstrated improvement, current evidence of prior satisfaction, or
an explicitly justified supersession or rejection. Missing evidence SHALL remain
open. A note, checkbox, extra artifact or larger skill SHALL NOT establish closure.

#### Scenario: A local example expresses a global obligation

- **WHEN** accepted feedback uses one defect to require a repository-wide principle
- **THEN** a bounded repair preserves the wider obligation and its remaining gaps
- **AND** closing the example does not close unverified sibling consumers

#### Scenario: A proposed resolution contains only prose

- **WHEN** feedback requires changed behavior but the candidate supplies only a retrospective or unchecked claim
- **THEN** the existing acceptance owner refuses closure for missing execution evidence
- **AND** neither additional headings nor task completion flags satisfy that obligation

#### Scenario: A mechanism has been changed and verified

- **WHEN** the responsible implementation or native policy changes and its distinguishing counterexample passes
- **THEN** evidence binds the candidate, applicable policy, environment and actual consumer
- **AND** required installation, publication or use observations remain separate conditions
- **AND** stale, contradictory or unrelated evidence cannot close the obligation

#### Scenario: A failure recurs despite an existing safeguard

- **WHEN** the same failure recurs after a claimed correction
- **THEN** closure reopens the failed safeguard's owner and examines why its prior check or guidance was ineffective
- **AND** the replacement removes the disproved path rather than adding another equivalent workaround

#### Scenario: A feedback procedure is selected during planning

- **WHEN** the current planning subject is feedback closure
- **THEN** the existing skill compiler selects repository governance and its canonical feedback rule
- **AND** package integrity and routing evidence do not claim host loading or successful agent behavior

#### Scenario: Feedback is already satisfied or contradicted by current facts

- **WHEN** current evidence establishes prior satisfaction or a justified rejection
- **THEN** the resolution preserves that evidence and its source scope without forcing unnecessary edits
- **AND** structural validation does not certify unrecorded conversation or complete intent understanding

### Requirement: Feedback preserves each repository's domain authority

ETHOS SHALL support feedback closure for self-hosting and adopted repositories
under their own accepted business meaning. The repository SHALL own goals,
constraints, success criteria and authorized judgments. Shared mechanisms and
capability adapters SHALL NOT replace those meanings with ETHOS-specific metrics
or imply business success from technical verification alone.

#### Scenario: Technical checks pass while a required business outcome fails

- **WHEN** a selected domain obligation has failed, missing or stale outcome evidence
- **THEN** its completion claim remains open despite green technical checks
- **AND** independently admissible source work can continue without claiming that outcome

#### Scenario: Different domains use the same protocol

- **WHEN** two adopters declare different business meanings and evidence providers
- **THEN** each is evaluated against its own accepted criteria through the shared owner
- **AND** neither acquires another repository's business policy, private context or authority

#### Scenario: A fresh authored correction follows an archived Change

- **WHEN** patch checks pass but requested paths are outside the attested archive effect's scope
- **THEN** admission remains blocked and directs the actor to fresh official intent
- **AND** it does not request another equivalent patch or expand historical write permission

### Requirement: Feedback can revise its governing model

Feedback SHALL distinguish implementation failure from inadequate methods,
governing models or problem framing. A demonstrated model gap SHALL select the
smallest sufficient Model Promotion, recompile dependent meanings, migrate
consumers and retire replaced mechanisms. Changes to goals or standards SHALL
require authorized intent alignment rather than outcome-driven relaxation.

#### Scenario: Local repairs do not resolve the contradiction

- **WHEN** valid counterexamples expose a missing distinction in the current model
- **THEN** the owning model is reconsidered before another equivalent local patch
- **AND** acceptance exercises the counterexample and preserved valid behavior after migration

#### Scenario: The feedback safeguard itself produces false closure

- **WHEN** its observations, interpretation or judgment contradict actual outcomes
- **THEN** the affected closure and safeguard are reopened for correction
- **AND** a note, new abstraction name or lower threshold cannot establish improvement

### Requirement: Publication continuation requests only missing observations

Locally ready publication with an unprobed configured peer SHALL select exact
remote observation before suggesting repeated local verification. The command
SHALL bind the current source HEAD and a policy-admitted destination ref: a
Work Lane maps to its proposal branch, while accepted and release branches
retain their roles. Cached tracking, local proof and remote effects SHALL
remain distinct evidence; observation grants no authority.

#### Scenario: A configured peer has not been probed

- **WHEN** local publication readiness passes with an unprobed peer
- **THEN** continuation selects the public exact-ref remote observation command
- **AND** cached synchronized tracking cannot replace that observation
- **AND** no local verification or remote publication effect is repeated

#### Scenario: Work Lane continuation uses a publishable destination

- **WHEN** a proved Work Lane is locally ready but its peer has not been probed
- **THEN** continuation names the policy-derived proposal ref, not its local Work Lane ref
- **AND** remote tracking and admission refer to that same proposal destination
- **AND** an ineligible source role cannot produce an impossible publish command

#### Scenario: No remote observation is available

- **WHEN** publication is local-only or its peers are unconfigured or unavailable
- **THEN** existing local fallback guidance and its evidence state remain available
- **AND** local readiness failure still blocks publication

### Requirement: Invocation-local intent selection

ETHOS SHALL resolve an explicit command or API Change before the invocation's
`ETHOS_CHANGE`, then use applicable native inference. The selected official
intent SHALL remain an input, independent of current mutation authority.
Absent selection SHALL preserve ambiguity; invalid selection SHALL fail closed.

#### Scenario: One selected product operation spans native consumers

- **GIVEN** an owned Work Lane contains two active official Changes
- **WHEN** an invocation selects one complete Change
- **THEN** prewrite, pre-tool, native commit, plan and proof consume that intent
- **AND** explicit command selection overrides the environment input
- **AND** removing the input restores unresolved selection
- **AND** holder mismatch remains a blocking authority gap

### Requirement: Exact proof query selects intent without weakening evidence

A proof query SHALL select the requested official intent, or the intent bound
to an explicitly selected Attestation. When both are explicit, they SHALL agree. Applicable evidence SHALL retain exact
source, policy, integrity, freshness and authority checks. Distinct intents
SHALL remain distinct queries; conflicting evidence for the same query SHALL
not be resolved by choosing a convenient proof.

#### Scenario: Several intents have proofs at the same source

- **WHEN** two official Changes have current proofs for one exact commit
- **THEN** an invocation selects only its own intent's proof
- **AND** an exact Attestation selection overrides the environment choice
- **AND** an unproven selected intent cannot borrow the other proof
- **AND** malformed evidence and same-intent contradictions remain blocking

#### Scenario: Explicit archive cannot borrow another intent's proof

- **GIVEN** two official Changes share the exact source and only one has proof
- **WHEN** archive explicitly requests the unproven Change
- **THEN** admission rejects before changing refs, index or content
- **AND** an environment-selected proof for the other Change cannot satisfy it

#### Scenario: Explicit archive remains selected through post-observation

- **GIVEN** the named Change has a current exact proof
- **WHEN** archive runs with an unrelated or invalid environment selection
- **THEN** admission and post-observation consume the explicit Change
- **AND** unselected intent remains unchanged and replay observes the prior effect

#### Scenario: Explicit proof constraints must agree

- **WHEN** a query names an Attestation and a different or invalid Change
- **THEN** it rejects instead of ignoring either explicit constraint
- **AND** matching active or attested archived intent remains admissible

#### Scenario: Several completed archives retain separate proof identities

- **GIVEN** two distinct accepted intents have verified archive effects
- **WHEN** either is explicitly selected at a later shared source commit
- **THEN** its exact archived acceptance remains available for proof and planning
- **AND** both contributed requirements and product results remain intact
- **AND** absent, unreadable, invalid or unverified intent is not silently accepted

#### Scenario: Full proof shares one current intent observation with audit

- **WHEN** full proof resolves an explicit intent that differs from its ambient default
- **THEN** governance audit consumes that same resolved OpenSpec observation
- **AND** it retains independent adopter, commit and release policy checks
- **AND** a new invocation observes current inputs rather than cached permission

### Requirement: External verification recovery follows its owning prerequisite

Required independent verification SHALL validate the configured provider before
requesting its receipt. Control replacement and publication SHALL share that
owner and report an actionable prerequisite without inventing evidence paths.
Every provider path component and symbolic-link hop SHALL be protected from the
current identity before it is read. Optional unselected verification SHALL
preserve local-first behavior.

#### Scenario: The required provider is unavailable

- **WHEN** its protected configuration is missing, unreadable or invalid
- **THEN** admission identifies that provider prerequisite and requests operator repair
- **AND** no repository effect or executable retry is presented as the repair

#### Scenario: A protected target is reached through a replaceable path

- **WHEN** a provider configuration, receipt store or signer anchor traverses a user-owned alias or writable ancestor
- **THEN** provider admission rejects that path even if its resolved target is system-owned
- **AND** a system-owned symlink chain with protected components remains eligible

#### Scenario: A configured provider has no valid receipt

- **WHEN** evidence is absent, outside the protected store, stale or incorrectly bound
- **THEN** admission requests valid evidence from the configured provider
- **AND** its configured store and issuer remain distinct from repository private state
- **AND** valid signatures, freshness and exact bindings are all required for success

### Requirement: Semantic carriers preserve singular authority

ETHOS SHALL preserve one editable owner per proposition across requirements,
design, tasks, implementation and evidence. Human and agent projections SHALL
identify their source and preserve scope and limitations. They SHALL NOT grant
acceptance, task progress, proof or permission by presentation alone.

#### Scenario: A behavior obligation changes

- **WHEN** a behavior changes relative to the accepted capability requirement
- **THEN** the selected Change owns the delta, design and acceptance cases
- **AND** docs and tools reference the owner rather than redefine the requirement
- **AND** disagreement with product invariants or observed execution stays explicit

#### Scenario: Research informs implementation

- **WHEN** sourced research supports a bounded implementation decision
- **THEN** research retains attribution and limits, while the Change owns the
  decision, experiment procedure, acceptance and task progress
- **AND** a summary does not become another editable requirement or result store

### Requirement: Structured documentation metadata preserves meaning

ETHOS SHALL preserve metadata identity, purpose, lifecycle and typed relationships
under valid syntax variations. Invalid declarations and unresolved required
authority targets SHALL be reported. Human-readable and machine-readable
representations SHALL agree on the same declared meaning.

#### Scenario: Equivalent and ambiguous metadata are distinguished

- **WHEN** metadata uses valid quoted scalars or structured relationships
- **THEN** public observation preserves the equivalent meaning
- **AND** duplicate keys and unclosed frontmatter cannot silently pass

#### Scenario: Required guidance is absent or contradictory

- **WHEN** a required authority target is missing or visible state contradicts metadata
- **THEN** public observation identifies the exact disagreement or missing target
- **AND** literal examples cannot satisfy actual reader-guidance obligations

#### Scenario: A selected documentation source disappears during observation

- **WHEN** a document selected by the registry becomes missing or unreadable before downstream checks finish
- **THEN** the public docs report identifies the unavailable source and blocks
- **AND** an earlier metadata observation cannot turn that incomplete read into a pass

#### Scenario: Selected documentation renders its title before metadata

- **WHEN** a profile-selected Markdown document encloses its leading YAML metadata in an HTML comment
- **THEN** the registry reads no metadata from it and reports the document's metadata as missing
- **AND** the repository paradigm names the comment wrapper to remove, so plain front matter is the only carrier

#### Scenario: Adopter-native guidance satisfies a portable reader floor

- **WHEN** an active profile-selected page has a visible H1 and non-empty non-heading text outside code fences, but not ETHOS-specific `Status`, `Purpose`, or `See also` labels
- **THEN** the docs report accepts its reader surface if metadata, relations, and navigation are valid
- **AND** a missing title or guidance hidden entirely in a literal fence blocks
- **AND** an authored empty or contradictory `Status:` remains a gap
- **AND** observational roles may omit reader guidance

### Requirement: ETHOS directory navigation uses README only

Current ETHOS-authored directory navigation SHALL use a necessary README.md.
Alternate index.md entrypoints and duplicate directory catalogs SHALL be rejected.
Topic links, immutable historical references and unrelated machine indexing
SHALL not be mistaken for authored directory entrypoints.

#### Scenario: A nested directory gains an alternate entrypoint

- **WHEN** authored directory navigation introduces an index.md carrier
- **THEN** quality reports the exact path and README-only correction
- **AND** it does not require a marker-only README as replacement

#### Scenario: One source serves human and agent readers

- **WHEN** rendered, raw or structured access resolves a current rule
- **THEN** the same source, scope, prerequisites and limitations remain available
- **AND** semantic hierarchy and meaningful links preserve progressive detail
  without fragmenting one cohesive explanation or duplicating authority
- **AND** a move repairs affected links without changing subject identity

### Requirement: Accepted history repair preserves original acceptance provenance

Accepted-source consumers SHALL resolve original acceptance through validated
completed history-repair relations for the exact accepted ref. They SHALL retain
the original Attestation and distinguish its coordinates from current source
coordinates. Equal trees alone SHALL NOT establish acceptance or authority.

#### Scenario: A repaired accepted source is proved and released

- **WHEN** governed history repair replaces an accepted commit and a new exact-source proof succeeds
- **THEN** closeout and release retain the original accepted-effect Attestation
- **AND** validated repair relations explain the current source coordinates
- **AND** current actor-owned Lease admission is independent of the proof's original execution root

#### Scenario: Related bytes do not prove current authority

- **WHEN** repair provenance is absent, ambiguous, cyclic or does not select the accepted ref
- **THEN** acceptance is not inferred from matching trees or a historical identity
- **AND** unrelated plans are not decoded as potential authority for that source

#### Scenario: Ordinary publication does not validate rewritten history

- **WHEN** a peer ref is already current, absent or an ancestor of the signed source
- **THEN** exact publication admission uses that observed relation without validating a historical repair
- **AND** a divergent peer still requires completed repair provenance or is rejected

### Requirement: Python reference observation respects binding and call site

Python consumer observation SHALL resolve statically determinable executable and
environment reads from import binding, lexical scope and values at the call.
Parsing a carrier SHALL NOT by itself establish semantic coverage. Unsupported
dynamic expressions SHALL report UNKNOWN for the affected obligation rather
than a fabricated reference or an unrelated whole-repository block. Patch
admission, repository audit and private-boundary consumers share this owner.

#### Scenario: Aliases preserve a real consumer

- **WHEN** `subprocess.run`, an aliased module or imported `run` invokes an undeclared executable, or aliased `os.getenv` reads an undeclared input
- **THEN** the public repository-audit gate identifies the corresponding missing declaration
- **AND** a spelling-only rewrite does not change the observed behavior

#### Scenario: Shadowing cannot invent an effect

- **WHEN** a local object named `subprocess` has a harmless `run` method
- **THEN** no standard-library executable consumer is inferred from that call
- **AND** the otherwise valid source remains eligible

#### Scenario: The value belongs to its scope and program point

- **WHEN** a global name is shadowed locally or assigned after `getenv(NAME)`
- **THEN** the read uses only values possible at that call in its lexical scope
- **AND** a later assignment cannot erase an earlier undeclared input

#### Scenario: Dynamic semantics remain bounded unknown

- **WHEN** a relevant callee or value uses unsupported dynamic lookup
- **THEN** only the affected consumer obligation is UNKNOWN and cannot pass as evaluated
- **AND** unrelated statically resolved files retain their valid result

### Requirement: Native command declarations own their executables

The common reference owner SHALL read executable ownership from the actual
trusted gate, profile and release command fields. Filename, product name and a
candidate's changed policy SHALL NOT supply missing prior authority. Missing,
malformed and genuinely undeclared commands remain distinct observations.

#### Scenario: A trusted command field supplies an executable

- **GIVEN** a trusted repository declaration selects an executable in a gate or local publication command
- **WHEN** maintained code references that executable
- **THEN** reference closure recognizes its exact declaration without a filename exception
- **AND** removing or corrupting the declaration exposes the appropriate gap

#### Scenario: Candidate command text cannot self-authorize

- **WHEN** a candidate adds both a new executable reference and its own command declaration
- **THEN** trusted-prior admission still rejects an unauthorized executable
- **AND** no broad allowlist or copied adopter declaration substitutes for that decision

### Requirement: Official artifact paths determine Change acceptance

ETHOS SHALL compile a selected Change from the official resolved artifact graph
and exact configured output paths. A fixed proposal, design or task filename
SHALL NOT override a valid project-local OpenSpec schema. Structural validation
and advisory guidance SHALL NOT by themselves prove accepted meaning or authorize
writes. The compiled result and proof identity SHALL bind the resolved paths and
bytes without creating another Markdown parser or intent carrier.

#### Scenario: A valid schema renames the design output

- **GIVEN** official status and strict validation accept a schema whose design output is `architecture.md`
- **WHEN** ETHOS compiles or proves the selected Change
- **THEN** it consumes that official output instead of requiring `design.md`
- **AND** changing the resolved path or its bytes invalidates the old binding

#### Scenario: Missing or ambiguous official outputs do not fall back

- **WHEN** official artifact resolution is absent, malformed, escapes the selected root or selects conflicting outputs
- **THEN** ETHOS reports the bounded source gap and grants no Change or path authority
- **AND** `skip_specs: true` remains a valid official no-spec case rather than an inferred omission

#### Scenario: Removal-only intent still compiles acceptance

- **GIVEN** official validation accepts a Change with only a `REMOVED` requirement and its reason and migration
- **WHEN** ETHOS compiles the selected acceptance
- **THEN** it records obligations for the resulting system instead of returning empty intent
- **AND** it does not require the retired behavior to remain true
- **AND** mixed add/remove, rename and valid no-spec Changes retain distinct meanings

### Requirement: CLI transport failure preserves the governance verdict

Result delivery SHALL distinguish a closed consumer, temporary backpressure and
partial output. Neither a caught write exception nor a short write may turn a
blocked governance result into process success or describe incomplete JSON as a
completed report. Already-performed effects SHALL NOT be replayed to repair the
output channel.

#### Scenario: A blocked result meets a full nonblocking pipe

- **WHEN** writing a blocked result raises `BlockingIOError`
- **THEN** the process retains a nonzero exit and a bounded transport diagnostic
- **AND** no additional repository effect is attempted

#### Scenario: JSON output is only partly accepted

- **WHEN** a stream reports a short successful write before the complete JSON frame
- **THEN** delivery is incomplete and cannot be treated as a passing report
- **AND** a genuinely closed consumer remains a distinct bounded failure

### Requirement: Cutover preserves exact predecessor supply

Before reclaiming a valid selected predecessor, installation SHALL preserve its
exact immutable runtime and wheel through the existing shared-installation
owner. Activation SHALL compare the originally captured selector bytes at its
effect boundary and report retained supply separately from activation and
reclamation. Historical provenance alone SHALL NOT pin local executables.

#### Scenario: A successful upgrade retires a local predecessor

- **WHEN** a valid selected predecessor is replaced by admitted shared supply
- **THEN** exact predecessor manifest, inventory and wheel remain available outside the repository before any local deletion
- **AND** the result identifies that retained supply without creating another selector
- **AND** repeated installation reuses identical bytes without adding generations

#### Scenario: Preservation or cutover fails

- **WHEN** predecessor preservation conflicts with unowned content or fails admission
- **THEN** original selector, hooks and state remain unchanged and no predecessor is reclaimed
- **AND** a later cutover failure restores the original activation without deleting retained supply

#### Scenario: Another installation changes selection

- **WHEN** selector bytes change after preparation and before cutover
- **THEN** native CAS rejects the stale operation without overwriting the peer or attempting compensation for an activation that did not occur
- **AND** preserved original and peer supply remain intact

#### Scenario: A local predecessor is already invalid

- **WHEN** independently admitted successor supply repairs an invalid local selected generation
- **THEN** installation reports unavailable rollback supply rather than claiming the damaged predecessor is preserved or valid
- **AND** uncertain predecessor bytes remain untouched under the existing reclamation owner

#### Scenario: Observation fails after selector replacement

- **WHEN** selector replacement occurred but its write acknowledgement or post-observation fails
- **THEN** the selector owner restores original bytes under its existing lock only when this operation still owns the desired selection
- **AND** a changed or unreadable peer selection remains intact with explicit compensation failure rather than false rollback success

### Requirement: Active proposals and designs follow their official templates

For every active Change, ETHOS SHALL resolve the artifact outputs and the schema's templates through the official OpenSpec CLI. Each proposal and design SHALL contain every literal heading of its resolved template, in template order and under its template parent. Sections that the template does not name SHALL remain allowed. When template drift is the only blocking governance gap, prewrite SHALL admit the selected Change's drifted proposal and design files, and no other path, for repair.

#### Scenario: A design omits an official section

- **WHEN** an active Change's design has no `Risks / Trade-offs` heading and its resolved template has one
- **THEN** OpenSpec governance reports the Change, the artifact and the missing heading, and plan and proof are not clean
- **AND** a design that adds `Migration Plan` or its own sections after the official ones has no gap

#### Scenario: A proposal nests a subsection under the wrong parent

- **WHEN** an active proposal places `### New Capabilities` under `## Impact` instead of `## Capabilities`
- **THEN** OpenSpec governance reports the misplaced heading and its template parent

#### Scenario: The resolved template gains a heading

- **WHEN** the template that the official CLI resolves for a Change's schema gains a literal heading
- **THEN** that heading is required of the Change's artifact without a change to ETHOS

#### Scenario: Drift that strict validation accepts is repairable

- **WHEN** an active Change passes strict validation, its design lacks a template heading, and that drift is the only blocking gap
- **THEN** prewrite in the owning Work Lane admits that design for repair
- **AND** prewrite of any other path reports that path as uncovered

#### Scenario: Another blocking gap keeps the repair closed

- **WHEN** template drift blocks together with another governance gap, such as an unavailable official CLI
- **THEN** prewrite admits no repair and reports the other gap

#### Scenario: Two drifted Changes do not hold each other's repair

- **WHEN** another active Change also lacks a template heading
- **THEN** the selected Change's drifted artifacts are still admitted for repair

### Requirement: Proof requires an archivable Change

Before the gates of a proof run, ETHOS SHALL archive the active Change that the proof selects with the official OpenSpec CLI in a disposable projection of the exact head and SHALL require official strict validation of the resulting specifications. The projection SHALL be removed and the repository tree SHALL remain unchanged.

#### Scenario: A MODIFIED requirement outgrows the archived limit

- **WHEN** an active Change modifies a requirement so that its text has 501 characters
- **THEN** proof fails before any gate runs and names the specification and the requirement
- **AND** the official change validation that passed does not satisfy this requirement

#### Scenario: An archivable Change is proved

- **WHEN** the simulated archive and its strict validation pass
- **THEN** the proof continues to its gates, and no file outside the disposable projection has changed

### Requirement: Greenfield formation produces a governed project

ETHOS SHALL form a usable Git repository only at an explicitly selected absent
destination. A foundation starter SHALL be domain-neutral; a selected domain
starter MAY add its own layout without making that layout ETHOS policy.

#### Scenario: A foundation project is formed

- **WHEN** an authorized exact formation plan targets an absent destination
- **THEN** the project has a real author-attributed initial commit, an accepted development ref, and a usable integration candidate ref with its own worktree
- **AND** it has an authored purpose, the one ETHOS profile, official OpenSpec configuration, and discoverable installed guidance.

#### Scenario: The first Change adds a capability

- **WHEN** a formed repository has official OpenSpec configuration but no accepted specs yet
- **THEN** a valid first ADDED Change can pass write admission without a placeholder `openspec/specs` directory or invented requirement
- **AND** an existing malformed or linked specs root remains invalid.

#### Scenario: A selected domain starter is composed

- **WHEN** the optional Python library starter is explicitly selected
- **THEN** the locked native generator's identity, version, inputs and outputs are bound to the reviewed plan
- **AND** ETHOS does not impose that starter's language, build tool or directory shape on other repositories.

#### Scenario: Formation records starter provenance

- **WHEN** the initial commit is created from a selected starter
- **THEN** a result Attestation binds that commit, generator version and exact generated path/digest subset
- **AND** the Attestation grants no permission to replace later authored bytes.

#### Scenario: A starter attempts unsafe output

- **WHEN** a generator fails, omits the selected library output, produces a link or special file, or a caller supplies an unknown starter or task spelling
- **THEN** formation rejects before publishing a target and reports the responsible generator or output boundary.

#### Scenario: The destination or prerequisite is not safe

- **WHEN** the destination or its planned candidate worktree exists, its parent cannot be trusted, or Git identity, official intent supply or product installation is unavailable
- **THEN** creation refuses before publishing a target and names the owning conflict or missing fact
- **AND** an existing project, foreign file or symlink target is not overwritten.

#### Scenario: An effect outcome is uncertain

- **WHEN** generation, Git creation, runtime activation or response delivery fails after an effect may have occurred
- **THEN** the result identifies confirmed effects and reports the unresolved remainder as UNKNOWN
- **AND** recovery reobserves before any retry; it does not repeat a possibly completed effect blindly.

#### Scenario: Candidate bootstrap is interrupted after its ref

- **WHEN** the candidate ref exists but its worktree or runtime activation is missing
- **THEN** status selects the candidate bootstrap's reviewed continuation before a hook-only repair when the worktree is missing
- **AND** status and bootstrap preview produce no effect; recovery preserves the initial commit.

### Requirement: Scaffold evolution preserves project authorship

Generated starter files SHALL become project-owned content after acceptance.
An upgrade SHALL compare the previous starter output, current customization and
new starter output; ETHOS SHALL not treat generator provenance as permission to
replace authored bytes.

#### Scenario: A starter evolves without conflict

- **WHEN** an explicitly selected versioned starter changes independently of project customization
- **THEN** a reviewed candidate preserves the customization and records the exact old and new inputs
- **AND** applying that candidate uses current repository admission rather than generator authority.

#### Scenario: A starter conflicts with customization

- **WHEN** a generated update and an authored edit compete for the same meaning or bytes
- **THEN** the conflict remains visible and unapplied until an authorized decision
- **AND** no update, uninstall or withdrawal silently deletes the authored result.

### Requirement: A legacy profile has one bounded repair path

An invalid existing profile SHALL NOT become runtime authority. A current owned
Work Lane MAY admit an exact patch touching only `.ethos/profile.toml` when its
postimage passes the strict profile model and preserves the committed repository
identity. The preview SHALL change no repository bytes.

#### Scenario: A reviewed profile repair is admitted

- **WHEN** a Work Lane holder supplies an exact single-profile patch from invalid bytes to a valid current binding with the same committed `profile_id`
- **THEN** prewrite admits that patch without accepting the old envelope as policy
- **AND** status, ordinary adoption and later repository effects retain their separate current checks.

#### Scenario: Missing coordination precedes a profile repair

- **WHEN** an authorized holder requests missing Lease restoration for one exact linked Work Lane whose accepted control root has an invalid historical profile
- **THEN** restoration binds the committed stable repository identity and the committed release-binding mirror policy, with paradigm defaults when none is declared
- **AND** an invalid declared release mirror or uncertain control root still blocks; preview and apply preserve refs, index, dirty bytes and the invalid profile
- **AND** the Lease does not make that profile runtime authority or authorize ordinary adoption, integration or publication.

#### Scenario: A profile repair lacks a trustworthy boundary

- **WHEN** the patch is absent, changes another path or identity, has an invalid postimage, or lacks Work Lane authority
- **THEN** prewrite blocks with the invalid-profile gap and a precise repair reason
- **AND** ETHOS does not automatically normalize or discard old fields; their meaning requires a reviewed disposition before integration.

#### Scenario: Staged bytes differ from working bytes

- **WHEN** the index contains an invalid profile but the working file is valid
- **THEN** staged admission rejects the index postimage before accepting a commit.

### Requirement: Active Change identity repair preserves complete source

ETHOS SHALL admit an exact relocation of one legacy temporally suffixed active
Change to its valid logical identity through the existing Work Lane prewrite and
staged admission owners. The complete regular source SHALL retain every byte,
file mode and unfinished task, with an unowned destination at the bound source
and baseline. This admission SHALL authorize identity repair only; current
authority and subsequent official validation, proof and delivery remain required.

#### Scenario: A complete legacy source moves without accepting unfinished work

- **WHEN** an owned Work Lane presents the complete matching delete/create patch
  or staged tree for one dated active Change and its logical root
- **THEN** native admission binds that exact source transition without changing
  the working preimage or index during observation
- **AND** every member and task retains its original content and state
- **AND** later authoring resolves the logical Change through ordinary native intent

#### Scenario: A transition does not match the complete current source

- **WHEN** member identity, bytes, modes, destination ownership, selected intent
  or fresh HEAD and staged-tree coordinates do not match the relocation
- **THEN** the transition acquires no identity-repair scope and preserves source
- **AND** current Lease, editor, runtime, profile and effect checks remain independent

### Requirement: Exact supporting template relocation restores native write admission

ETHOS SHALL admit one exact supporting-template relocation from the canonical
spec root to a distinct template in the current repository-local native schema.
The admitted patch SHALL preserve the original authored content, all concrete
reference destinations, the selected complete Change and all other obligations.

#### Scenario: A supporting template blocks its own corrective move

- **WHEN** the current native root audit rejects that regular Markdown member
  and the owned Work Lane supplies its exact relocation patch
- **THEN** prewrite admits only the template move and parser-derived link changes
- **AND** ordinary writes, proof and remaining strict validation stay blocked
- **AND** the official delta template is not overwritten or relabeled as metadata

#### Scenario: Unbound source or incomplete consumers cannot gain repair scope

- **WHEN** the patch changes authored meaning, omits a concrete consumer, targets
  another owner or carries unrelated work
- **THEN** it does not acquire supporting-relocation admission
- **AND** missing official observations, stale configuration, another Change or
  unrelated governance gaps preserve the blocking decision
- **AND** historical code mentions and unrelated references remain unchanged

### Requirement: Adoption rejects invalid existing intent configuration before binding

Adoption SHALL consume the existing official OpenSpec configuration audit before
writing any binding. Preserving authored bytes SHALL NOT imply accepting an
invalid carrier. CLI, SDK and MCP SHALL share this decision and retain its gaps.

#### Scenario: Existing OpenSpec configuration fails its owning audit

- **WHEN** adoption previews or applies with malformed, missing-schema or forbidden-root configuration
- **THEN** it reports the OpenSpec path conflict and the owning audit's reasons
- **AND** no profile or configuration is written, existing bytes remain unchanged, and continuation requires resolving that conflict

#### Scenario: A valid authored configuration differs from the default

- **WHEN** its owning audit passes
- **THEN** adoption preserves its exact bytes and does not replace its schema, context or rules
- **AND** this preservation does not certify full mutation readiness or executed proof

### Requirement: Signed object transport preserves non-product meaning

The existing publication declaration SHALL select explicit `transport_tags`
scopes for non-product signed input objects. Product tag scopes SHALL take
precedence. Transport SHALL reuse review-object qualification, not product
version, accepted-release or repository-proof obligations.

#### Scenario: An admitted signed input is transported

- **WHEN** an exact annotated tag matches a scope declared in the trusted peer baseline
- **THEN** public publication and native pre-push use the same role and introduced-range checks
- **AND** signature trust, native tag-header identity, declared peer, exact source and immutable-ref CAS remain required
- **AND** replay observes the same result without authorizing replacement or another peer

#### Scenario: Candidate configuration cannot grant itself transport authority

- **WHEN** the prior trusted policy omits the scope or also selects a product tag
- **THEN** candidate-authored transport configuration does not override that policy
- **AND** automatic transport baselines follow native peer HEAD, its committed protected-root policy and the same peer's accepted ref, not a candidate-authored accepted designation
- **AND** malformed scopes, missing baselines, untrusted signatures, renamed tag headers and tag replacement remain rejected

### Requirement: Explicit repository identity transition

ETHOS SHALL permit a typed, explicitly authorized repository identity transition
through existing GitEffect, TransitionPlan, Attestation and CAS owners. Each
authorization SHALL bind one target ref, exact pre/post commits and trees,
old/new identities, one object database, accepted intent/proof, actor and current
Lease generation. Ordinary cross-identity CAS SHALL remain rejected.

#### Scenario: Identity changes progress through independently authorized stages

- **WHEN** a proven new-identity work lane explicitly integrates into an old-identity candidate
- **THEN** only the exact admitted target ref transitions and its result uses the new identity
- **AND** accepted and release refs may transition later under separate fresh authorizations
- **AND** unrelated refs are not changed to manufacture a global singleton identity

#### Scenario: Missing or contradictory authority cannot cross identities

- **WHEN** the semantic operation is unsupported or database identity, ancestry, target coordinates, intent/proof, actor or Lease generation is missing, stale or contradictory
- **THEN** admission preserves all refs and reports the owning refusal
- **AND** a shared object database does not make different profiles equivalent

#### Scenario: A completed authorization is not consumed twice

- **WHEN** the same exact transition is replayed after completion
- **THEN** recovery observes the original effect and result without repeating its mutation
- **AND** the original exact coordinates resolve to the original Attestation while invented coordinates remain rejected
- **AND** a later target-ref transition requires its own authorization
- **AND** partial or unknown execution is observed before any further effect

#### Scenario: Ref completion leaves checkout materialization pending

- **WHEN** the exact ref transition succeeds but its linked checkout synchronization fails
- **THEN** preview reports pending materialization rather than completed acceptance
- **AND** authorized recovery validates the original result and synchronizes only the admitted preimage without repeating the ref effect
- **AND** missing authorization, stale coordination and unrelated user edits remain rejected
- **AND** restored original content remains admissible despite stale stat metadata, without refreshing index bytes during observation

#### Scenario: Renaming does not retain an obsolete current product identity

- **WHEN** a target has completed its admitted old-to-new identity transition
- **THEN** its current results use the new identity without aliases or compatibility mappings
- **AND** old revisions remain historical or not-yet-transitioned stage inputs
- **AND** no temporary profile rollback or history rewrite is required

#### Scenario: Retirement deletes a ref that predates a completed rename

- **WHEN** a retirement only deletes a topic ref whose head carries the identity of its common ancestor with every kept ref
- **THEN** the deletion is admitted under the kept identity without an identity edge, alias or profile rewrite
- **AND** an identity introduced only by the deleted ref, or a ref without shared history, remains rejected
- **AND** an integration that moves a ref across identities still requires the explicit transition

#### Scenario: A ref program contains both migration and new publication refs

- **WHEN** an admitted branch identity transition also creates a signed tag or follows a declared accepted-mirror policy
- **THEN** only existing branches whose identities change receive identity edges
- **AND** new tags and unchanged-identity refs remain in the same exact ref program without invented pre-identities

#### Scenario: Preview preserves the selected transition

- **WHEN** an identity transition is previewed before applying it
- **THEN** no ref changes and its continuation retains the exact root, source, target and explicit identity mode
- **AND** a future signed tag is distinguished from the branch scope already admitted by that preview

### Requirement: Adopter runtime selection preserves incumbent enforcement

Explicit native adoption MAY select the exact immutable package runtime independently of
hook installation. Preview SHALL bind the source build and current selector. Authorized apply
SHALL use the existing runtime materialization and compare-and-swap owners, preserve incumbent
Git configuration and hooks, and compensate failed selection without overwriting intervening
state. Runtime provenance SHALL NOT imply hook enforcement, source qualification or delivery.

#### Scenario: Incumbent domain hooks remain active during adoption

- **WHEN** an owned adopter explicitly selects the runtime through native adoption
- **THEN** the selected package may validate tracked-write provenance without replacing its hooks
- **AND** hook, domain, signing, full-proof and delivery obligations remain independently required
- **AND** preview, missing authorization or a stale selector produces no runtime-selection effect

### Requirement: Supplemental OpenSpec metadata has explicit native ownership

An adopter MAY bind exact non-executable capability metadata filenames to existing repository
authority files in its typed profile. Required normative specs SHALL remain authoritative;
metadata SHALL NOT establish domain correctness. An identity-preserving profile repair MAY
resolve this shape conflict only
when it changes these bindings alone and satisfies every other admission obligation without
mutating its preimage.

#### Scenario: Native capability metadata coexists with normative specs

- **WHEN** declared metadata is valid, regular and bound to its existing native owner
- **THEN** OpenSpec observation preserves both the metadata and required normative spec
- **AND** each capability retains one required regular `spec.md`
- **AND** undeclared files, unsafe names, symlinks, missing owners and malformed metadata fail closed
- **AND** absent specs and unrelated profile weakening remain inadmissible

### Requirement: Applicable shared quality is supplied by the product

ETHOS SHALL select shared documentation, native carrier and official intent
obligations from actual authored inputs. Its source and installed execution
SHALL use the same shipped native verifier, locked supply and mandatory policy.
Adopter checks and tool configuration MAY add requirements but SHALL NOT replace
or disable the shared floor. Focused diagnosis SHALL remain distinguishable
from the complete applicable proof closure.

#### Scenario: A document repository retains its native development workflow

- **WHEN** its authored Markdown and OpenSpec inputs select common obligations
- **THEN** the product composes those obligations with existing adopter checks
- **AND** no ETHOS Python development environment or copied quality controller is required

#### Scenario: Local policy attempts to disable a shared rule

- **WHEN** a repository's native configuration disables a common Markdown rule or supplies competing discovery configuration
- **THEN** the mandatory shipped policy still checks the same exact authored inputs
- **AND** local configuration cannot hide a shared failure, skip an input or cause source mutation

#### Scenario: Native configuration has one formatter and independent semantics

- **WHEN** original locked Prettier accepts authored JSON or YAML structure
- **THEN** shared configuration checks accept that formatting without a competing serializer or layout rule
- **AND** native syntax, duplicate keys and undeclared aliases remain independently checked
- **AND** package-manager dependency records and explicitly bound source inputs keep their original owners and bytes
- **AND** native policy errors and formatting refusal block without source writes

#### Scenario: Native formatter and linter have distinct responsibilities

- **WHEN** official Prettier accepts a tight list with a nested fenced block
- **THEN** semantic Markdown lint accepts its container structure while still rejecting empty links
- **AND** check refusal preserves bytes, native fixing succeeds and a second fix leaves bytes unchanged
- **AND** secure native YAML preserves nested heading parameters without a vendor patch or dependency downgrade

#### Scenario: Native source check and fix share one exact selection

- **WHEN** authored inputs select the installed source-format capability
- **THEN** preview and check prepare the same original native postimages without writes
- **AND** an authorized fix requires current HEAD, actor, Work Lane and Lease admission for the complete patch
- **AND** source bytes, modes and index are re-observed before effect, the index and HEAD remain unchanged, and a second fix is a no-op
- **AND** literal names, native ignore controls and byte-exact formatting pragmas retain their meanings
- **AND** foreign source, immutable evidence, dependency records and generated projections retain their owners
- **AND** missing inputs remain unknown while unsafe paths, native parse errors and conflicting policy refuse without source writes
- **AND** Nox and proof project this same owner, while independent semantic gates remain required

#### Scenario: A Decision Record has no authored choice

- **WHEN** a current decision record omits a core role or supplies only comments, quotations, code or one multi-role section
- **THEN** the portable Docs Registry rejects the unproven role
- **AND** distinct canonical sections and meaningful authored rationale are checked within the profile-selected documentation root

#### Scenario: An adopter uses the canonical five-section Decision Record

- **WHEN** a current record has distinct `Context`, `Decision`, `Alternatives Rejected`, `Consequences and Boundary`, and `Evidence and Revisit` sections in that order
- **THEN** the shared registry checks visible authored rationale in every section through the same portable contract
- **AND** the selected documentation-root name does not change its identity or section grammar
- **AND** missing, quoted, hidden, or code-only rationale remains unproven; no adopter-local parser or exemption is required

### Requirement: Source acceptance preserves the declared native audit owner

Local-source proof SHALL derive dependency-audit applicability from the exact
declared full gate policy. It SHALL preserve all selected native checks and
existing captured-input, scope, freshness and disposition obligations. A native
adopter SHALL NOT acquire Python audit inputs from an unrelated product floor.

#### Scenario: A native adopter has its own complete proof floor

- **WHEN** every declared native check and required product observation passes
- **THEN** proof issuance and consumption use that exact native policy
- **AND** they do not impose an undeclared canonical Python audit

#### Scenario: A declared canonical audit is omitted

- **WHEN** local-source planning selects a subset missing the declared canonical audit
- **THEN** it blocks before executing the subset
- **AND** a saved partial proof cannot authorize a candidate transition

#### Scenario: A declared native dependency check fails

- **WHEN** the repository's selected native dependency check fails
- **THEN** no passing proof is issued and the candidate ref remains unchanged
- **AND** canonical audit findings, expiration and source bindings retain their original refusals

### Requirement: Accepted closeout leads a self-hosted root through re-arming

When accepted closeout advances a root whose hook runtime it built from the replaced accepted head and that runtime is no longer current, the closeout SHALL name the repository's `bootstrap` verb as its next action instead of `ethos publish`. A hook runtime built from any other source keeps `ethos publish` as the next action.

#### Scenario: The advance stales the self-hosted hook runtime

- **WHEN** closeout advances `dev` from the head its current hook runtime was built from
- **THEN** the next action runs `bootstrap` in the accepted root instead of `ethos publish`

#### Scenario: An adopter runs an installed runtime

- **WHEN** closeout advances an adopter whose hook runtime was built from an ETHOS source
- **THEN** the next action stays `ethos publish`

### Requirement: Publication peer names default from their declaration

The peer ID and Git remote name SHALL be configurable; the paradigm keeps a governed
repository's remote equal to its peer ID. Within an explicit peer declaration only, an omitted ID SHALL default to the declared provider and an omitted Git remote
SHALL default to the resolved ID. Defaults SHALL NOT create undeclared peers, infer a provider or
rename existing remotes. Explicit empty or invalid names and duplicate resolved identities SHALL
fail closed before observation or mutation.

#### Scenario: Selected providers use conventional configurable defaults

- **WHEN** GitLab or GitHub is explicitly declared without an ID or Git remote name
- **THEN** the resolved names SHALL be `gitlab` or `github` respectively
- **AND** an explicit ID or remote SHALL replace only its corresponding default
- **AND** no `origin` remote or undeclared provider SHALL be introduced

#### Scenario: Several independently named instances share one provider

- **WHEN** peers `gitlab_a`, `gitlab_b` and `github` are explicitly declared
- **THEN** both GitLab peers SHALL use the GitLab adapter without sharing identity
- **AND** publication SHALL support selecting any declared subset independently

### Requirement: Changed-scope Skill routing is explicit

ETHOS SHALL route changed-scope skill requests through explicit activation
metadata and changed-path evidence rather than subject or identifier substring
matches.

#### Scenario: Changed scope route is explicit

- **WHEN** `ethos plan --changed --json` runs
- **THEN** each selected Skill matches its declared route subject, an activation
  path glob, or the current operation
- **AND** a passing activation lists each selected Skill's id, path, and
  operation in `data.skill_activation` with its ordered pre-read, rule, and
  post-check obligations
- **AND** a missing required Skill, an unavailable Skill observation, or a
  dependency cycle is reported as a required gap

### Requirement: Status separates coordination advisories from blockers

ETHOS SHALL expose non-blocking advisory governance signals in the bounded
status reader without treating them as transition-blocking required gaps.

#### Scenario: Status carries Work Lane coordination advisories

- **WHEN** `ethos status --json` runs and workspace status reports Work Lane
  coordination signals such as `foreign_work_lane_present` or
  `coordination_gap:scope_overlap:<branch>`
- **THEN** `summary.coordination_advisory_count` counts the reported signals
- **AND** advisory signals do not become status `required_gaps`
- **AND** when a foreign or unbound Work Lane is visible and no other
  continuation applies, `next_action` is the read-only `ethos lane status --json`

#### Scenario: Status carries Work Lane coordination blockers

- **WHEN** workspace status contains a required coordination gap such as
  `coordination_gap:current_scope_unknown`
- **THEN** that gap appears in status `required_gaps`
- **AND** `summary.coordination_blocking` is true
- **AND** status remains read-only and does not authorize foreign Work Lane
  cleanup

### Requirement: Generated artifact topology binds the root project environment

ETHOS SHALL classify generated outputs by lifecycle and audit both files and
executable producers. The ignored root `.venv` that `uv.lock` selects SHALL be
each checkout's single Python environment; an active producer that executes
through the retired `build/runtime/venv` home SHALL report a required gap.

#### Scenario: An executable entrypoint uses the retired runtime home

- **WHEN** generated-artifact topology audits a `tools/`, `.github/`, or
  `.gitlab-ci.yml` producer whose active text executes through
  `build/runtime/venv`
- **THEN** the audit reports
  `generated_artifact_entrypoint_retired_venv_runtime:<path>`
- **AND** proof remains blocked until the producer uses the root `.venv`

#### Scenario: The root project environment is an allowed runtime home

- **WHEN** topology classifies the ignored root `.venv`
- **THEN** it is the repository-local virtual environment that `uv.lock` selects
- **AND** it remains disposable host-local state, neither tracked nor promoted
  as repository truth

### Requirement: Publish readiness separates remote observation from execution

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

#### Scenario: Reachable but non-synchronized remote is an available target

- **WHEN** a declared remote is available but its tracking comparison is not
  `synchronized`
- **THEN** `data.publication.remote_state` SHALL be `target_available`, or
  `targets_available` when several declared peers are all available
- **AND** the command SHALL not claim a remote push or hosted-CI result
