# ETHOS Adapters

## Purpose

ETHOS SHALL connect repository lifecycle semantics to provider-specific Git,
SQLite, process, package-manager, hosted CI, and protocol runtimes without
treating any provider as product truth.
## Requirements
### Requirement: Exact-request Mutation Admission
Only a `pass` verdict may authorize an effect; `block` and `unknown` both fail closed.

ETHOS SHALL block apply-mode land and publish unless execution confirmation,
expected HEAD binding, applicable Commitments, current facts, and required
Evidence admit the exact request. Confirmation SHALL NOT authenticate a caller
or create reusable authorization.

#### Scenario: Apply mode is requested
- **WHEN** `ethos land --apply` or `ethos publish --apply` runs
- **THEN** ETHOS requires explicit confirmation and expected HEAD before any
  mutation can proceed
- **AND** the decision binds action, resource, expected state, policy refs,
  evidence refs, and decision basis
- **AND** it mints no role, token, session, or reusable permission.

### Requirement: Work Lane Topology
ETHOS SHALL classify linked worktrees by lane role and surface foreign Work
Lanes without entering their file trees.

#### Scenario: Role policy is projected
- **WHEN** `ethos status --json` or `ethos lane status --json` reports
  workspace topology
- **THEN** the payload includes `role_policy`
- **AND** the role order is
  `release_root -> accepted_root -> candidate -> work_lane -> proposal_lane`
- **AND** `branch_bindings` follow that semantic order before branch name
- **AND** host navigation labels are not product state
- **AND** adapters derive presentation from `worktree_binding` rather than
  owning branch, lane, or mutation semantics

#### Scenario: Foreign Work Lanes exist
- **WHEN** `ethos status` or `ethos lane status` inspects a repository with a
  linked `work/*` lane outside the current checkout
- **THEN** ETHOS reports the foreign lane path, branch, head, and role from git
  worktree metadata
- **AND** ETHOS reports `foreign_work_lane_present` as a coordination signal
- **AND** ETHOS does not read, modify, close, or clean the foreign lane
- **AND** ETHOS reports a non-authoritative action preview with observe as the
  only candidate action and write, land, and retire blocked
- **AND** actual mutation re-evaluates its exact current request.

### Requirement: Prewrite Admission
ETHOS SHALL gate tracked writes through the current Work Lane role and editor
root binding before files are edited.

#### Scenario: Protected root write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from an accepted
  root, candidate, proposal lane, detached checkout, or unknown lane
- **THEN** ETHOS blocks the request with `protected_lane_prewrite_blocked`

#### Scenario: Owned Work Lane write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane whose editor root matches the checkout root
- **THEN** ETHOS admits the write and returns a structured admission report

#### Scenario: Work Lane write lacks editor-root binding
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane without editor-root binding
- **THEN** ETHOS blocks the request with `editor_root_missing`

### Requirement: Lease-backed Lane Start
ETHOS SHALL acquire local lease records when creating Work Lanes through the
public lane command plane.

#### Scenario: Work Lane start is applied
- **WHEN** `ethos lane start <name> --commitment <path> --apply --holder-ref
  <holder-ref>` runs from a clean accepted root with a valid matching Commitment
  and succeeds
- **THEN** ETHOS creates a `work/<name>` linked worktree
- **AND** ETHOS records an active lease in host-local state under
  `<git-common-dir>/ethos/state.sqlite`, outside every checkout
- **AND** raw Git worktree creation is not treated as standard ETHOS workflow
  state because it has no ETHOS lease or claim boundary

#### Scenario: Existing Change continuation is applied
- **WHEN** `ethos lane start <name> --source-root <source-work-lane> --apply
  --holder-ref <holder-ref>` explicitly requests continuation from a clean owned
  source Work Lane
- **THEN** ETHOS copies its exact Lease-bound Commitment carrier
- **AND** it does not evaluate fresh bootstrap.

#### Scenario: Work Lane start intent is absent or ambiguous
- **WHEN** neither a Commitment nor source Work Lane is supplied, or both are
  supplied
- **THEN** ETHOS blocks before creating a worktree, Lease, or ref.

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --apply --holder-ref <holder-ref>` runs from an
  existing `work/*` lane or a dirty accepted root
- **THEN** ETHOS blocks the request with
  `lane_start_requires_clean_accepted_root`

### Requirement: Admission Before Product Audit
ETHOS SHALL evaluate apply-mode mutation admission before running product
repository-audit checks.

#### Scenario: Apply mode is blocked by lane admission
- **WHEN** `ethos land --apply` or `ethos publish --apply` is invoked from a
  protected root with explicit authorization and expected HEAD
- **THEN** ETHOS returns structured `blocked` JSON with
  `protected_root_mutation`
- **AND** ETHOS does not require the target repository to contain ETHOS product
  repository governance schemas before reporting the admission failure

### Requirement: Evidence Locality
ETHOS SHALL keep local runtime state separate from durable evidence.

#### Scenario: Evidence is emitted
- **WHEN** ETHOS creates proof evidence
- **THEN** the evidence is HEAD-bound, digest-addressed, and separate from
  ignored local runtime state

### Requirement: Bounded External Evidence Adapters

ETHOS SHALL verify external identity assertions, signed independent-verification
or hosted-enforcement receipts, and control-replacement verifier receipts only
when the applicable Commitment requires them. Adapters SHALL store no
credentials and SHALL NOT mint authority. Provider-local verifier and Git-hook
executables SHALL be supplied and governed by the operator outside the ETHOS
product source and distribution surface while conforming to the provider-neutral
receipt contract.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires the receipt, verifier executable, candidate proof,
  and bootstrap Chronicle decision to reside outside the candidate tree and bind
  both heads, both control digests, verifier digest, proof digest, and bootstrap
  decision digest
- **AND** the candidate proof is a native executed `ethos prove --execute --json`
  result with `command = "prove"`, `verdict = pass`, `state = "proven"`,
  `data.executed = true`, and matching candidate HEAD bindings in
  `data.evidence.head` and `data.provenance.predicate.head`
- **AND** a hand-authored `{head, state}` envelope is not accepted as candidate
  proof
- **AND** missing or unverifiable provenance returns `unknown`.

#### Scenario: Control removal and branch-role changes cannot evade admission

- **WHEN** a candidate changes `.ethos/workspace.toml`, deletes a control path,
  or renames a control path into a non-control location
- **THEN** closeout treats the source control path as changed and requires the
  same candidate-external receipt
- **AND** an unavailable Git diff returns `unknown` and blocks closeout.

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention for a protected ref transition
- **THEN** the provider boundary requires a valid signed
  `IndependentVerificationReceipt` before Git accepts the update
- **AND** the receipt exactly binds the remote, proposed commit and tree, action,
  proof-floor ID and digest, gate-policy digest, verifier implementation digest,
  issuer, key ID, validity window, and signature
- **AND** local hooks, provider configuration, or independent re-execution
  without complete hosted mediation do not prove prevention.

#### Scenario: independent re-execution requires an exact signed receipt

- **WHEN** ETHOS projects `independently_reexecuted` for a transition
- **THEN** the provider receipt binds the exact remote, commit, tree, action,
  proof-floor ID and digest, gate-policy digest, verifier implementation digest,
  issuer, key ID, validity window, and signature
- **AND** local hooks or provider configuration alone neither establish
  `independently_reexecuted` nor prove prevention.

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** an operator enables independent verification or generic Git
  pre-receive enforcement
- **THEN** the executable implementation resides outside the ETHOS product
  source and distribution surface
- **AND** it consumes the published provider-neutral receipt contract without
  creating product policy, credentials, accounts, network services, daemons, or
  scheduling requirements.

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** a provider has not installed a conforming generic Git pre-receive
  adapter or its protected provider-local configuration selects `disabled`
- **THEN** ordinary ETHOS adoption, status, plan, prove, land, and local
  publication readiness require no account, key, receipt store, daemon, network
  service, or named service user
- **AND** the adapter does not mint authority or alter product lifecycle truth.

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** a provider-enabled conforming pre-receive adapter receives a
  non-deletion update for a configured protected ref
- **THEN** it accepts the update only when its provider-store receipt has a
  valid protected-anchor signature and exactly binds the configured remote,
  proposed commit, proposed tree, action, proof-floor ID/digest, gate-policy
  digest, and verifier implementation digest
- **AND** it rejects absent, stale, failed, malformed, unsigned, or mismatched
  receipts before Git accepts the ref.

#### Scenario: An update is outside the configured protected set

- **WHEN** a conforming generic Git pre-receive adapter receives an update for a
  ref not named by its provider-local protected-ref configuration
- **THEN** it does not require a receipt for that ref
- **AND** it does not execute a client-supplied command or infer policy from the
  proposed tree.

#### Scenario: The server adapter remains a thin physical extension

- **WHEN** GitHub, GitLab, independent-identity, or generic Git providers project
  external enforcement
- **THEN** they conform to the same receipt and decision contract
- **AND** no provider executable becomes a second governance kernel or a
  required ETHOS distribution asset.

### Requirement: Cross-host Handoff Adapter

ETHOS SHALL transfer content-addressed Git and context artifacts, never the
source SQLite lease. Preserved tracked and non-ignored untracked work SHALL be
restored before the destination lease is acknowledged, and partial imports
SHALL roll back branch and worktree residue.

#### Scenario: preserved handoff is imported safely

- **WHEN** a verified preserved handoff package is imported into a clean
  accepted-root clone
- **THEN** ETHOS creates a destination-local branch, worktree, lane incarnation,
  and lease
- **AND** restores tracked and non-ignored untracked content before acknowledgement
- **AND** rolls back branch and worktree state if restoration or lease creation fails.

### Requirement: Internal ETHOS Gate Fast Path
ETHOS SHALL execute internal ETHOS JSON gates in-process when safe.

#### Scenario: Internal gate runs without nested CLI process
- **WHEN** the local runner executes `python -m ethos.cli <command> --json`
- **THEN** ETHOS invokes the command plane in-process
- **AND** external provider commands still use the subprocess adapter

### Requirement: Official OpenSpec Lifecycle Adapter

The official OpenSpec CLI SHALL own validation and archival for ETHOS's selected
self-profile carrier. ETHOS SHALL consume its current `doctor`, `list`, `status`,
and strict `validate` observations, then apply only Commitment and scope checks.
Generic adopters SHALL not require OpenSpec.

#### Scenario: official active state is malformed or ambiguous

- **WHEN** official `list --json` has an invalid wire shape, an absent explicitly
  requested Change, or multiple implicitly selectable Changes
- **THEN** ETHOS blocks with a precise gap
- **AND** it does not select by timestamp, directory order, task-file parsing,
  fallback field names, or a private rank.

#### Scenario: a completed Change remains active

- **WHEN** official `list` reports status `complete` for a Change still under the
  active changes surface
- **THEN** land and accepted-root closeout report
  `openspec_completed_change_unarchived:<change>`
- **AND** only the owner-native archive action can clear the active fact.

#### Scenario: historical archives use an older shape

- **WHEN** a historical archive contains obsolete names, metadata, tasks, or
  delta layout
- **THEN** ETHOS preserves it as non-authorizing history
- **AND** current admission does not re-run or reinterpret that historical
  workflow.

### Requirement: Work Lane Claim Binding Projection
ETHOS SHALL expose Work Lane ownership as claim boundary evidence for
trust-bearing mutation.

#### Scenario: Work Lane has a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane with a bound claim id
- **THEN** the lane report includes the claim id as boundary evidence
- **AND** the lane report does not mark the claim promoted by lane presence
  alone

#### Scenario: Work Lane lacks a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane without a bound claim id
- **THEN** the lane report remains usable for local work
- **AND** trust-bearing closeout reports a missing claim-binding gap

### Requirement: Intake Adapter Projection Boundary
ETHOS SHALL keep intake and Backlog provider state as projection or intake
evidence rather than repository truth.

#### Scenario: Intake provider reports done state
- **WHEN** an intake provider reports a task as complete
- **THEN** ETHOS records the intake state as projection evidence
- **AND** ETHOS still requires claim admission, OpenSpec lifecycle readiness,
  executed proof, and promotion targets before trust closeout

### Requirement: Optional tool adapters remain replaceable
ETHOS SHALL expose optional adapter boundaries for environment runners, graph
systems, task ledgers, external workflow frameworks, and agent method packs
without making them product substrate. Useful external practices MAY be mapped
to ETHOS contracts, adapters, evidence classes, projections, or method packs
only through accepted governance changes that keep lifecycle truth inside the
ETHOS kernel contract.

#### Scenario: Adapter profile is reported

- **WHEN** `ethos audit --mode deep --json` reports tool adapters
- **THEN** Nox, Pixi, Pants, task-ledger, and agent-method-pack entries SHALL be
  visible as adapter-only boundaries
- **AND** their output SHALL NOT replace ETHOS proof, OpenSpec lifecycle checks,
  claims, evidence, or Git-native Work Lane semantics.

#### Scenario: External workflow frameworks are classified
- **WHEN** ETHOS evaluates Comet, Spec Kit, BMAD, Superpowers, Task Master, Agent OS, OpenSPDD, Shotgun, or fspec
- **THEN** their useful practices may be mapped to ETHOS contracts, adapters, evidence classes, projections, or method packs
- **AND** their command planes, hidden state directories, task stores, and phase names do not become ETHOS lifecycle truth by default

### Requirement: Protected ref hooks bind semantic evaluation to promoted control

ETHOS SHALL keep the accepted checkout as the fail-closed shell-hook boundary
for an accepted-ref transaction. When that transaction promotes a candidate
head, it SHALL evaluate the semantic ref-admission reducer using a clean linked
checkout of the configured candidate branch at that exact promoted head.

#### Scenario: candidate control implementation differs from accepted checkout

- **GIVEN** the accepted checkout contains an older control implementation
- **AND** the configured candidate checkout is clean, bound to the configured
  candidate branch, and resolves to the promoted candidate head
- **AND** the candidate changes admission or proof-policy behavior
- **WHEN** official accepted-root closeout advances the accepted ref
- **THEN** the protected hook SHALL run the candidate-tree semantic evaluator
  against the candidate head
- **AND** it SHALL bind runner source, candidate checkout, candidate head, and
  transition fields explicitly
- **AND** it SHALL not reject solely because accepted-old source would compute
  a different policy result.

#### Scenario: candidate semantic runner cannot be bound

- **WHEN** the configured candidate checkout is missing, dirty, detached,
  stale, or its semantic runtime cannot be bound to that checkout
- **THEN** the accepted-ref hook SHALL reject the transition
- **AND** it SHALL not fall back to accepted-old semantic source.

#### Scenario: changed managed shell hook bootstraps an accepted-to-release mirror

- **GIVEN** the candidate policy enables `release_mirror = "accepted_ff"`
- **AND** the candidate changes the tracked `reference-transaction` shell hook
- **AND** the incumbent shell can admit the accepted transition only through the
  candidate semantic runner
- **WHEN** official closeout performs the hook deployment bootstrap
- **THEN** it SHALL advance the accepted ref through an ordinary exact-intent,
  proof-bound compare-and-swap
- **AND** it SHALL synchronize the accepted checkout before advancing the
  release mirror through the promoted shell hook
- **AND** it SHALL not use a direct ref update, hook disablement, or hook-path
  override
- **AND** it SHALL report incomplete release-mirror bootstrap residue rather
  than accepted closeout when the second transition cannot complete.

### Requirement: Lifecycle mutation has one semantic owner

ETHOS SHALL expose each lane lifecycle and retirement operation from its owning
adapter module. Public CLI routing SHALL call that owner directly and SHALL NOT
reconstruct an equivalent Runtime graph in a forwarding facade.

#### Scenario: CLI invokes a lifecycle operation

- **WHEN** a lane refresh or retirement command resolves its implementation
- **THEN** it SHALL call the semantic owner directly
- **AND** no compatibility forwarding function, re-export, alias, service locator,
  or Runtime-composition factory SHALL remain.

#### Scenario: adapter behavior needs a test seam

- **WHEN** a test replaces one effectful dependency
- **THEN** it SHALL patch the semantic owner module directly
- **AND** production APIs SHALL NOT carry a Runtime object or runtime parameter.

#### Scenario: retirement reads lease state

- **WHEN** retirement evaluates current leases
- **THEN** it SHALL reuse the canonical repository status lease projection
- **AND** a second SQLite-only lease reader SHALL NOT remain.

### Requirement: Adopter Release Metadata Remains Profile Bounded

ETHOS SHALL NOT infer product release semantics from the presence of a generic
tool configuration file, and SHALL report supported runtime-files identity
without requiring Python package metadata.

#### Scenario: Runtime-files adopter is audited

- **WHEN** an adopted repository has `pyproject.toml` without `[project]`
- **AND** one `[tool.<name>]` table declares `distribution = "runtime-files"`
  and a contained `version-source`
- **THEN** generic coupling and schema audits do not execute ETHOS product-only
  release policy
- **AND** direct release inspection reads the table name and declared version
  file as release identity
- **AND** malformed or unsupported metadata is returned as a structured gap,
  not a Python traceback
- **AND** invalid release-policy TOML is likewise returned as a structured gap

### Requirement: Atomic Fresh Change Bootstrap

ETHOS SHALL start a new mutation-capable Work Lane from clean accepted truth
only when one explicit valid Commitment and the exact official OpenSpec Change
identity are available before the Work Lane ref is created.

#### Scenario: A fresh Change starts without a predecessor lane

- **WHEN** an operator supplies a valid Commitment for a new Change from a clean
  accepted root with a current clean candidate
- **THEN** ETHOS creates and validates the official OpenSpec carrier in a
  detached candidate-based worktree
- **AND** binds the resulting exact HEAD, tree, Commitment path, bytes, digest,
  holder, and Lease generation before creating the Work Lane ref
- **AND** ordinary tracked writes remain blocked until that transaction passes.

#### Scenario: Bootstrap intent is absent or ambiguous

- **WHEN** neither a live source Work Lane nor an explicit fresh Commitment is
  supplied, or both are supplied
- **THEN** ETHOS blocks before creating a worktree, Lease, or ref
- **AND** it does not infer intent from an archive, accepted spec, branch name,
  historical task, or conversation.

#### Scenario: A live Change continuation is requested

- **WHEN** an operator explicitly supplies a clean owned source Work Lane with
  a valid exact Lease-bound Commitment
- **THEN** ETHOS preserves the existing exact source-carrier continuation
  semantics
- **AND** the fresh bootstrap path is not also evaluated.
