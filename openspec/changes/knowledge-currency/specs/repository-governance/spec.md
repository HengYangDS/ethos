## MODIFIED Requirements

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
- **THEN** an accepted decision Attestation has already bound the exact policy
  and target
- **AND** a fresh two-phase decision binds one exact observation and recovery
  plan
- **AND** dirty content is preserved before retirement
- **AND** a stale observation blocks the effect instead of falling back to raw
  Git deletion.

#### Scenario: local convergence completion keeps evidence planes separate

- **WHEN** all cohort intent has been integrated or explicitly superseded
- **THEN** strict carrier completion, HEAD-bound executed proof, candidate
  landing, accepted-root closeout, and lane retirement are verified as distinct
  transitions
- **AND** retained custody remains independent
- **AND** local completion does not claim remote push, hosted execution, or
  distribution publication.

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
- **AND** retirement uses one exact reviewed-content receipt from
  `ethos lane retire abandon` that binds the accepted HEAD, the exact target
  content, and the four-field Lease observation when present
- **AND** any later accepted, target, or Lease drift blocks apply until a new
  observation and receipt exist.

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
- **THEN** retirement requires an exact reviewed-content receipt whose custody
  is preserved outside the retiring resource before any destructive effect
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
- **AND** bind a fresh official Change as the continuation before a new merge,
  proof, closeout, remote update, or proposal deletion is attempted
- **AND** the continuation SHALL re-observe the current inputs and retain its
  newly observed proposal tip through ordinary merge ancestry.

#### Scenario: Divergent proposal patch is reconciled

- **WHEN** a configured remote proposal ref is not an ancestor of the current
  candidate head
- **THEN** an owned Work Lane bound to the selected official Change records its
  exact tip and integrates it with an ordinary merge
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

### Requirement: Versioned local-state schema evolution

ETHOS SHALL support only the current Lease schema: a `leases` table keyed by
`lane_ref` with `holder_ref`, a positive `generation` and `expires_at`, and
ownership limited to `leases`. Ordinary readers SHALL reject other shapes without
rewriting the database; only runtime activation migrates the exact previous
canonical shape. The database path SHALL derive from Git common-directory
identity; destructive linked retirement still requires the accepted checkout.

#### Scenario: A fresh state database is initialized

- **WHEN** no state schema exists
- **THEN** ETHOS creates the current Lease schema
- **AND** SQLite enforces one row per `lane_ref`
- **AND** it does not create a database-wide migration ledger.

#### Scenario: A version-1 state database is opened

- **WHEN** an ordinary reader opens a database whose `leases` table has a
  retired shape
- **THEN** ETHOS fails closed without translating or rewriting the database
- **AND** only hook installation migrates the exact previous canonical shape or
  applies the authorized reset.

#### Scenario: Another owner shares the state database

- **WHEN** the current lease table coexists with tables owned by another
  local-state capability
- **THEN** lease initialization validates only its exact owned schema subset
- **AND** it preserves every unrelated table and row unchanged.

#### Scenario: A current database is initialized again

- **WHEN** the exact current Lease schema already exists
- **THEN** initialization is idempotent
- **AND** no active coordination row is rewritten or deleted.

#### Scenario: The accepted branch is not checked out

- **WHEN** another protected branch occupies the canonical repository path
- **THEN** a linked Work Lane reads the same Lease generation
- **AND** destructive retirement still requires its accepted-checkout control root.

### Requirement: Bounded Coordination Aggregate Detail State

ETHOS SHALL derive coordination aggregate detail state from the reader mode
selected by the caller, not from the number or contents of visible foreign Work
Lane rows.

#### Scenario: Empty bounded inventory remains deferred

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `ethos status --json` observes workspace status with foreign
  path-scope expansion disabled
- **THEN** `summary.coordination_detail_state` SHALL be `deferred`
- **AND** observable foreign-lane, unbound-lane, and missing-Lease counts SHALL
  remain available.

#### Scenario: Empty full inventory remains exact

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `ethos lane status --json` runs its full workspace observation
- **THEN** `summary.coordination_detail_state` SHALL be `exact`
- **AND** `dirty_foreign_work_lane_count` SHALL be zero.

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

- **WHEN** an accepted takeover authorization admits replacing one complete
  foreign Lease generation
- **THEN** ETHOS applies the same exact-generation transfer used by ordinary
  holder transfer
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

## ADDED Requirements

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

### Requirement: Mutation admission is bound to explicit repository context

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

#### Scenario: refresh-base keeps every replay conflict blocked

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts on any path
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

### Requirement: Work Lane lifecycle resolves from current facts

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

#### Scenario: lane handoff is recorded as a decision Attestation

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

### Requirement: Work Lane base refresh reports success only on candidate ancestry

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

### Requirement: Handoff contracts reject coercion and ambiguous object IDs

Handoff contracts SHALL reject coercive scalar values and Git object IDs whose
width is not exactly 40 or 64 hexadecimal characters.

#### Scenario: A wire payload relies on coercion or an ambiguous object ID

- **WHEN** a handoff payload supplies a boolean as an integer, a Lease generation
  as a string or boolean, or a Git object ID of intermediate width
- **THEN** both the typed contract and its JSON Schema boundary reject it
- **AND** no lifecycle effect begins.

## REMOVED Requirements

### Requirement: Coupling Binding Registry

**Reason**: The coupling registry was replaced with native owners in `9f76c2e3e`, which deleted `system/coupling.toml` and `src/ethos/repository/policy/coupling/`; no source emits `binding_registry`.

**Migration**: Bindings stay with their native owners: gates in `system/gates.toml` ("Tool adoption remains profile and adapter scoped"), peers in `.ethos/release.toml` ("Declared publication peer topology"), and the profile ("Repository profile is a strict current binding").

### Requirement: Standards Adapter Lifecycle

**Reason**: `system/standards.toml` was deleted in `9f76c2e3e`, and the repository audit (`src/ethos/repository/audit.py`) has no standards adapter report.

**Migration**: "Tool adoption remains profile and adapter scoped" requires a gate in `system/gates.toml` and a native configuration or supply owner for each active tool.

### Requirement: Changed Scope Playbook Routing

**Reason**: Its scenario "presence-only skills do not close report scoring" names status scoring, deleted with `packages/ethos/src/ethos/domain/reporting/scoring.py` in `62c3fe6d2`, and the `playbook_changed_path_unmatched` gap left `src/ethos/assistants/playbooks.py` in `3d393c93a`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Changed-scope Skill routing is explicit"; presence-only scoring has no successor.

### Requirement: Reference Adopter Parity Closure

**Reason**: The tracked parity evidence `evidence/parity/alphasim-dmgr-shadow.json` was deleted in `067457a51`, and the parity package `src/ethos/repository/evidence/parity/` in `3d393c93a`; no source reports parity gaps.

**Migration**: None. Adopter terms stay out of product code under the kernel requirement "Product Core Adopter Isolation".

### Requirement: Context-bound mutation admission

**Reason**: Its scenario "refresh-base resolves parity projection-only conflicts as stale projection" names a recovery removed from `src/ethos/adapters/mutation/lane_lifecycle/refresh.py` in `3d393c93a`; every conflicting replay now aborts. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Mutation admission is bound to explicit repository context", which keeps the other scenarios.

### Requirement: Work Lane Lifecycle Resolution

**Reason**: Its scenario "lane handoff is recorded as Chronicle resolution" contradicts its own body and the requirement text; the Chronicle owner `src/ethos/adapters/mutation/resolution/chronicle.py` was deleted in `ed18713a0`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Work Lane lifecycle resolves from current facts", with the same text and scenarios.

### Requirement: Advisory governance signals are visible in reader views

**Reason**: `advisory_gap_count`, `gap_layers`, and `state=advisory` were deleted with `packages/ethos/src/ethos/domain/report.py` and `domain/reporting/gaps.py` in `62c3fe6d2`, and two scenario titles name those layers. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Status separates coordination advisories from blockers".

### Requirement: Evidence-bound preservation-package clearing

**Reason**: `lane_resolution/clear-preservation` and its Chronicle gate were deleted with `src/ethos/adapters/mutation/resolution/lane.py` and `resolution/chronicle.py` in `ed18713a0`, and Chronicle has no current reader.

**Migration**: Reviewed nontracked content is disposed of only under "Reviewed content retirement binds the exact destructive preimage".

### Requirement: Worktree-bound semantic runtime bootstrap

**Reason**: Python execution moved to each checkout's root `.venv` in `01eac3afe`, and `tools/ci/scripts/with-python-runtime.sh`, which read `ETHOS_RUNTIME_BOOTSTRAPPED`, was deleted in `cbf439019`. `src/ethos/repository/policy/artifact_entrypoints.py` now rejects `build/runtime/venv`.

**Migration**: "Generated artifact topology binds the root project environment"; uv selects the root environment natively.

### Requirement: Explicit execution overrides remain bounded

**Reason**: `ETHOS_PYTHON` left the source in `63515de9e`, and `tools/ci/scripts/with-python-runtime.sh`, which read `ETHOS_UV_CACHE_DIR` and `PYTHON`, was deleted in `cbf439019`; `UV_CACHE_DIR` is uv's native setting.

**Migration**: None. uv owns its cache setting, and "Generated artifact topology binds the root project environment" fixes the environment.

### Requirement: Generated Artifact Topology Contract

**Reason**: Root `.venv` became each checkout's single environment in `01eac3afe`, and `src/ethos/repository/policy/artifact_entrypoints.py` now rejects `build/runtime/venv`; host-bootstrap exemptions were removed in `5be29f5d4`. Both scenario titles describe the retired topology. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Generated artifact topology binds the root project environment".

### Requirement: Protected-root probe remediation is reader-only

**Reason**: The orientation reader `packages/ethos/src/ethos/domain/orient.py` that derived probe remediation was deleted in `62c3fe6d2`; `src/ethos/domain/inspection.py` derives none.

**Migration**: "Temporary test probe provenance remains explicit and bounded" keeps probe classification in workspace status.

### Requirement: Fresh Work Lane bootstrap avoids unnecessary runtime admission

**Reason**: The checkout-local hook `.githooks/reference-transaction` that carried this exception was deleted in `815fc546a`; hooks now run the Git-common selected runtime, and `src/ethos/adapters/repo/hook/protocol.py` skips equal non-zero updates for every ref.

**Migration**: "Git-common hook runtime activation is singular" and "Work Lane start is no-clobber and compensation-bound".

### Requirement: Work Lane refresh success is ancestry-bound

**Reason**: Its scenario "parity-projection recovery preserves the same success condition" names a recovery removed from `src/ethos/adapters/mutation/lane_lifecycle/refresh.py` in `3d393c93a`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Work Lane base refresh reports success only on candidate ancestry".

### Requirement: Publish readiness distinguishes observed remote synchronization from execution

**Reason**: Its scenario "Reachable but non-synchronized remote remains deferred" has been false since `17cb214c7` changed `packages/ethos/src/ethos/domain/land/publication.py`; an available unsynchronized peer reports `target_available` (`src/ethos/domain/publication/inspection.py`). OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Publish readiness separates remote observation from execution".

### Requirement: Status distinguishes local publication and hosted observation state

**Reason**: The status report and its `local_publication_projection` were deleted with `packages/ethos/src/ethos/domain/report.py` and `domain/reporting/gaps.py` in `62c3fe6d2`; `src/ethos/domain/inspection.py` projects neither state.

**Migration**: Local publication readiness: "Publish readiness separates remote observation from execution". Hosted observation: the `hosted_observation` Nox session (`tools/ci/hosted_observation.py`).

### Requirement: Shadow parity external execution honors checkout runtime topology

**Reason**: Shadow parity and its `external_command_failed` gap were deleted with `src/ethos/adapters/shadow/core.py` in `3d393c93a`.

**Migration**: None.

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

**Reason**: Its effect owner `src/ethos/adapters/mutation/resolution/_effects.py` was deleted in `ed18713a0`. Its Commitment and decision-Attestation prerequisites contradict PDC 281-287, which binds no Commitment to a topic retirement.

**Migration**: "Absorbed local resource retirement is independent of authoring role" and "Retained Topic Retirement".

### Requirement: Explicit conservative local-state maintenance

**Reason**: The local-state maintenance owner `src/ethos/adapters/store/state/maintenance.py` was deleted in `3d393c93a`, and the local-state audit `tools/ci/local_state_audit.py` in `8c0e6b457`.

**Migration**: None. Git-common Lease state changes only through runtime activation (runtime-activation "Runtime activation includes Git-common state").

### Requirement: Ref-bound proof retention

**Reason**: Proofs are now Attestations in the Git-native set (`src/ethos/adapters/mutation/proof.py`), and the explicit maintenance that pruned proof records (`src/ethos/adapters/store/state/maintenance.py`) was deleted in `3d393c93a`.

**Migration**: "Attestation lifetimes end with the transition that consumes them".

### Requirement: Recovery material is preservation-bound before cleanup

**Reason**: Recovery snapshot inventory lived in `src/ethos/adapters/store/state/maintenance.py`, deleted in `3d393c93a`, and its Chronicle receipt has no current reader.

**Migration**: Required custody is preserved before reviewed retirement ("Linked Work Lane retirement has one exact effect").

### Requirement: Tracked lifecycle does not imply local-state maintenance effects

**Reason**: Its digest-bound maintenance apply (`apply_local_state_maintenance` in `src/ethos/adapters/store/state/maintenance.py`) was deleted in `3d393c93a`; hook installation now migrates Lease state.

**Migration**: runtime-activation "Runtime activation includes Git-common state".

### Requirement: Real history-residue effects use a distinct local closeout successor

**Reason**: It records one dated successor for a maintenance receipt whose owner `src/ethos/adapters/store/state/maintenance.py` was deleted in `3d393c93a`.

**Migration**: None. Its control-replacement scenario is covered by "Control replacement preserves trusted prior verification".

### Requirement: Lease generation transitions compile from one declaration

**Reason**: The tracked declaration `system/lifecycle.toml` was deleted in `8b53af332`, and the handoff offer and accept operations were removed in `5efb74405`; `src/ethos/adapters/mutation/lane_lifecycle/lease/operation.py` applies renew, resume, and transfer.

**Migration**: "Lease generation identity is complete across boundaries".

### Requirement: Resolution Decisions and Receipts are semantically disjoint

**Reason**: Lane-resolution Decisions and completion Receipts, including `decision_id`, were deleted with `src/ethos/adapters/mutation/resolution/` in `ed18713a0`; its scenario "A resolution effect completes" has no subject. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Handoff contracts reject coercion and ambiguous object IDs" for the surviving handoff contracts.

### Requirement: Ownerless closeout admission is consumed at the effect boundary

**Reason**: The ownerless closeout effect `src/ethos/adapters/mutation/resolution/closeout/ownerless/` was deleted in `ed18713a0`.

**Migration**: "Work Lane lifecycle resolves from current facts" (landed retirement without a live Lease), "Linked Work Lane retirement has one exact effect", and "Destructive Work Lane retirement is a resumable observed transition".

### Requirement: Deployed adopter readers remain bounded

**Reason**: The fixture `tests/fixtures/adopter-terminal-v1/` and terminal-v1 transition validation were deleted in `ddeb577e0`, and adopted transition-row validation in `691cb4a40`.

**Migration**: None.
