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

### Requirement: Ownerless closeout admission is consumed at the effect boundary

**Reason**: The ownerless closeout effect `src/ethos/adapters/mutation/resolution/closeout/ownerless/` was deleted in `ed18713a0`.

**Migration**: "Work Lane lifecycle resolves from current facts" (landed retirement without a live Lease), "Linked Work Lane retirement has one exact effect", and "Destructive Work Lane retirement is a resumable observed transition".

### Requirement: Deployed adopter readers remain bounded

**Reason**: The fixture `tests/fixtures/adopter-terminal-v1/` and terminal-v1 transition validation were deleted in `ddeb577e0`, and adopted transition-row validation in `691cb4a40`.

**Migration**: None.
