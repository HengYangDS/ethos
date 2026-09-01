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
ETHOS SHALL classify linked worktrees by local repository role and SHALL keep remote review refs outside local authoring authority.

#### Scenario: Role policy is projected
- **WHEN** `ethos status --json` or `ethos lane status --json` reports workspace topology
- **THEN** local role order is `release_root -> accepted_root -> candidate -> work_lane`
- **AND** a configured `proposal/*` target is classified only by publication admission as `proposal_ref`
- **AND** no proposal ref grants local authoring or Lease authority.

#### Scenario: Foreign Work Lanes exist
- **WHEN** `ethos status` or `ethos lane status` inspects a repository with a
  linked `work/*` lane outside the current checkout
- **THEN** ETHOS reports the foreign lane path, branch, head, and role from Git
  worktree metadata
- **AND** ETHOS reports `foreign_work_lane_present` as a coordination signal
- **AND** ETHOS does not read, modify, close, or clean the foreign lane
- **AND** ETHOS reports a non-authoritative action preview with observe as the
  only candidate action and write, land, and retire blocked
- **AND** actual mutation re-evaluates its exact current request.

### Requirement: Prewrite Admission
ETHOS SHALL admit tracked authoring only from an owned `work/*` lane.

#### Scenario: Protected root write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from an accepted
  root, candidate, detached checkout, or other non-Work-Lane checkout
- **THEN** ETHOS blocks the request with `protected_lane_prewrite_blocked`.

#### Scenario: Owned Work Lane write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane whose editor root matches the checkout root
- **THEN** ETHOS admits the write and returns a structured admission report.

#### Scenario: Work Lane write lacks editor-root binding
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane without editor-root binding
- **THEN** ETHOS blocks the request with `editor_root_missing`.

#### Scenario: Proposal ref is checked out locally
- **WHEN** `ethos lane prewrite` evaluates tracked mutation from a `proposal/*` checkout
- **THEN** the checkout has no authoring role
- **AND** ETHOS blocks the write rather than suggesting that the proposal ref is a Work Lane.

### Requirement: Lease-backed Lane Start

ETHOS SHALL create a Work Lane from the exact candidate object, acquire one
Git-common Lease generation, and then require official OpenSpec intent before
tracked authoring. Raw Git worktree creation is not governed Work Lane state
because it lacks the Lease relation.

#### Scenario: Work Lane start is applied

- **WHEN** the public command creates a lane from a clean accepted repository
- **THEN** it creates the exact worktree/ref and one Git-common Lease generation
- **AND** it creates no tracked Commitment carrier, Claim boundary, or mirrored Git coordinates

#### Scenario: Existing Change continuation is applied

- **WHEN** work continues in an already owned clean Work Lane
- **THEN** ETHOS retains the same lane and Lease relation and re-observes current Git and OpenSpec facts
- **AND** it copies no intent carrier or repository coordinates

#### Scenario: Work Lane start intent is absent or ambiguous

- **WHEN** a new Work Lane has no active official OpenSpec Change
- **THEN** lane creation remains complete
- **AND** tracked product authoring remains blocked until exactly one official Change exists

#### Scenario: Work Lane start is requested from a non-accepted or dirty root

- **WHEN** lane start runs from an existing Work Lane or dirty accepted root
- **THEN** ETHOS blocks before mutation

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

External identity, hosted-enforcement, and control-replacement evidence SHALL be
validated only when the selected Commitment requires its exact Attestation
predicate and bindings. An external adapter stores no credentials and mints no
authority.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof, schema, hook, identity, or
  enforcement controls
- **THEN** closeout requires candidate-external proof and decision Attestations
  binding both heads, control digests, verifier digest, proof digest, and
  decision identity
- **AND** a hand-authored summary or historical Chronicle cannot satisfy it

#### Scenario: Control removal and branch-role changes cannot evade admission

- **WHEN** a candidate deletes, renames, or changes a declared control
- **THEN** closeout requires the same exact Attestation query
- **AND** an unavailable diff blocks rather than returning pass

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention
- **THEN** a provider receipt Attestation binds remote, commit, tree, action,
  proof and policy digests, verifier, issuer, validity, and signature
- **AND** local hooks or provider configuration alone do not prove prevention

#### Scenario: independent re-execution requires an exact signed receipt

- **WHEN** ETHOS projects independent re-execution
- **THEN** the exact signed receipt Attestation binds the same hosted facts
- **AND** local re-execution alone does not satisfy the hosted predicate

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** an operator enables external verification
- **THEN** its executable remains outside ETHOS product source and distribution
- **AND** it consumes the provider-neutral Attestation contract

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** no provider-local adapter is enabled
- **THEN** ordinary local governance requires no account, key, daemon, or store
- **AND** no missing provider adapter mints or removes authority

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** an enabled adapter receives a protected update
- **THEN** it admits only an exact valid signed provider receipt Attestation
- **AND** malformed, stale, failed, unsigned, or mismatched evidence blocks

#### Scenario: An update is outside the configured protected set

- **WHEN** a provider adapter receives an update outside its protected set
- **THEN** it does not require the hosted predicate for that ref
- **AND** it does not infer policy from the proposed tree

#### Scenario: The server adapter remains a thin physical extension

- **WHEN** any Forge or generic Git provider projects enforcement
- **THEN** it conforms to the same Attestation query
- **AND** it does not become a second governance kernel

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

### Requirement: Intake Adapter Projection Boundary

Intake and Backlog provider state SHALL remain input Attestations or read-only
projection rather than repository truth.

#### Scenario: Intake provider reports done state

- **WHEN** an intake provider reports a task complete
- **THEN** the occurrence may be preserved and selected for a successor
  Commitment
- **AND** it does not replace OpenSpec readiness, executed proof, or exact
  operation Attestation queries

### Requirement: Optional tool adapters remain replaceable

Optional runners, graph systems, task ledgers, workflow frameworks, and method
packs MAY project into Commitment, Attestation, Facts, or derived plans. Their
commands, hidden stores, task state, and phase names SHALL NOT become ETHOS
lifecycle or semantic roots.

#### Scenario: Adapter profile is reported

- **WHEN** an optional adapter emits a result
- **THEN** it remains an input or derived projection
- **AND** it cannot replace Commitment, Attestation, proof, or Git-native Work
  Lane semantics

#### Scenario: External workflow frameworks are classified

- **WHEN** ETHOS evaluates an external workflow framework
- **THEN** useful values may map into the two-root model or derived plans
- **AND** the framework command plane and hidden state remain non-authoritative

### Requirement: Protected ref hooks bind semantic evaluation to promoted control

ETHOS SHALL keep the accepted checkout as the fail-closed shell-hook boundary
for an accepted-ref transaction. When that transaction promotes a candidate
head, it SHALL evaluate the semantic ref-admission reducer using a clean linked
checkout of the configured candidate branch at that exact promoted head. The
hook SHALL consume the exact prepared accepted-head admission decision owned by
public closeout and SHALL NOT independently reconstruct proof, topology, or a
precondition that the protected local ref already equals the promoted object.

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
- **AND** it SHALL consume the same prepared ref intent and proof decision as
  closeout
- **AND** it SHALL not reject solely because accepted-old source would compute
  a different policy result.

#### Scenario: candidate semantic runner cannot be bound

- **WHEN** the configured candidate checkout is missing, dirty, detached,
  stale, or its semantic runtime cannot be bound to that checkout
- **THEN** the accepted-ref hook SHALL reject the transition
- **AND** it SHALL not fall back to accepted-old semantic source
- **AND** it SHALL project the complete public closeout command required to
  repair or retry the exact transition.

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

#### Scenario: an exact protected object is pushed after local closeout

- **GIVEN** public closeout admitted and post-observed an exact signed candidate
  object through its prepared ref intent
- **WHEN** pre-push evaluates that same object for the declared protected role
- **THEN** the hook SHALL consume the admitted object and proof identity
- **AND** it SHALL not demand an additional hook-local role transition or a
  circular local-ref equality condition.

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

ETHOS SHALL create a mutation-capable Work Lane and its official OpenSpec Change
through one bounded public transition from clean accepted truth. The Lease SHALL
bind only lane, holder, generation, and expiry; the resulting Git ref and
OpenSpec artifacts SHALL be re-observed as fresh facts.

#### Scenario: A fresh Change starts without a predecessor lane

- **WHEN** an operator supplies a Change name and holder from a clean accepted root with a current clean candidate
- **THEN** ETHOS creates the exact Work Lane and official OpenSpec artifacts
- **AND** no tracked Commitment carrier, predecessor ledger, or Lease mirror is created

#### Scenario: Bootstrap intent is absent or ambiguous

- **WHEN** the Change name, target lane, holder, accepted root, or candidate is missing or ambiguous
- **THEN** ETHOS blocks before the first effect or compensates only its exact owned effects
- **AND** it does not infer intent from an archive, branch name, historical task, or conversation

#### Scenario: A live Change continuation is requested

- **WHEN** an operator continues a valid active Change in its owned Work Lane
- **THEN** ETHOS reuses that lane and official Change
- **AND** the fresh bootstrap path is not also evaluated

### Requirement: Attestations use one deterministic Git set carrier

The sole current Attestation carrier SHALL be a canonical hash-sharded Git tree
selected by `refs/ethos/attestations-set`. Its root SHALL be a deterministic
parentless commit over fixed metadata. An update SHALL be exactly the union of
the observed set and validated canonical members followed by exact CAS.

#### Scenario: Concurrent writers add different Attestations

- **WHEN** one writer loses the set-ref CAS race
- **THEN** it re-observes the selected set and recomputes the deterministic union
- **AND** the successful root contains both immutable members

#### Scenario: A member is added repeatedly or collides

- **WHEN** canonical bytes for an existing identity are added again
- **THEN** the root is unchanged
- **AND** different bytes for the same identity fail closed

#### Scenario: Set membership is evaluated

- **WHEN** an Attestation exists in the selected set
- **THEN** membership proves preservation only
- **AND** an operation still validates predicate, payload, relations, verifier,
  bindings, validity, and selected Commitment

### Requirement: Non-authoritative Attestation stores are not current readers

Git-common JSON directories and operation indexes MAY stage or cache bytes but
SHALL NOT select current Attestations or authorize effects after cutover.
Historical Claim and Chronicle bytes SHALL remain inert Git history.

#### Scenario: A stale local Attestation exists

- **WHEN** it is absent from the selected Git set
- **THEN** status, planning, proof, and effects ignore it as current evidence
- **AND** no compatibility scan silently promotes it

### Requirement: Shared external process execution has one adapter owner

ETHOS SHALL execute shared external argv commands through one provider-neutral
process adapter. The Git adapter SHALL own only Git executable resolution and
Git-specific semantics; it SHALL NOT own the generic command runner used by
OpenSpec, hooks, runtime activation, or host-native authorities. Process
creation failures SHALL preserve the exact argv, working directory, and
operating-system cause at the public diagnostic boundary.

#### Scenario: A non-Git command cannot be created

- **WHEN** an ETHOS adapter invokes an exact non-Git command and the operating
  system rejects process creation
- **THEN** the failure is classified as process execution rather than Git
  execution
- **AND** its evidence contains the exact argv, working directory, and original
  operating-system cause.

#### Scenario: Git process creation fails

- **WHEN** the Git adapter resolves Git but the operating system rejects that
  exact process creation
- **THEN** the public failure retains Git-specific classification
- **AND** the same exact argv, working directory, and original operating-system
  cause remain available.
