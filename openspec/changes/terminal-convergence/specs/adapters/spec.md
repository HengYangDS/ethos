## ADDED Requirements

### Requirement: Workstation-independent Product Kernel
ETHOS source, schemas, tests, docs, install, lifecycle, and recovery MUST have zero dependency on a workstation-specific control plane.

#### Scenario: ETHOS runs on a clean supported host
- **WHEN** no external workstation-control executable, package, schema,
  environment variable, or endpoint exists
- **THEN** local adoption, status, planning, proof, lane lifecycle, recovery, and installation remain functional

### Requirement: Explicit Adapter Classes
Fact providers, change carriers, gate providers, effect executors, attestation
sinks, projections, and scaffolds MUST declare their consumer, permissions,
protocol version, configuration reference, evidence-artifact contract, and
retirement condition through profiles or manifests.

#### Scenario: An adapter requests an undeclared effect
- **WHEN** its requested path or mutation is outside the manifest permission set
- **THEN** admission blocks before invoking the adapter

#### Scenario: An adapter has no reproducible configuration or evidence binding
- **WHEN** its declared consumer cannot locate the exact configuration or bind
  output to the declared evidence-artifact contract
- **THEN** adapter proof resolves to `block` or `unknown`
- **AND** the adapter contributes no lifecycle authority

### Requirement: No Premature In-process Plugin Framework
Extensions MUST use data or subprocess JSON first and MAY use standard-library entry points only for demonstrated trusted consumers; the core MUST NOT require a DI container, event bus, or pluggy-style framework.

#### Scenario: A single internal implementation requests a plugin layer
- **WHEN** no independent extension consumer exists
- **THEN** the abstraction is rejected and explicit composition remains the terminal implementation

### Requirement: ChangeContract Parsing Fails Closed
Lifecycle MUST parse every reviewed active `contract.toml` even when the current
changed-path set has no material path.

#### Scenario: A malformed contract has no matching material path
- **WHEN** lifecycle review reads the Change
- **THEN** it reports `change_contract_invalid:<change>` rather than treating file existence as validity

### Requirement: Terminal Adapter Compilation And Evidence

The adapters capability SHALL preserve the migrated operational boundaries while using ChangeContract and Attestation as its only persistent semantic entities. Fresh RepositoryFacts and prior Attestations SHALL compile a transient PlanIR; new Attestations SHALL record verifier-bounded outcomes, and historical views SHALL remain derived projections.

#### Scenario: Work Lane has a valid base-bound Lease
- **WHEN** ETHOS inspects a current `work/*` lane whose strict Lease is valid
- **THEN** the lane report includes `base_change_contract_digest` and
  `contract_binding = bound`
- **AND** prewrite, PlanIR, proof, handoff, head advance, and closeout require
  the selected ChangeContract digest to equal that base digest

#### Scenario: Work Lane Lease is unverifiable or absent
- **WHEN** ETHOS observes an expired, malformed, legacy, mismatched, or absent
  Lease row
- **THEN** the lane reports exactly `expired`, `unknown`, or `missing`
- **AND** the lane is observe-only rather than usable for mutation or implicit
  conversion

## MODIFIED Requirements

### Requirement: Lease-backed Lane Start
A Work Lane Lease SHALL persist only coordination identity and the immutable
base ChangeContract digest. The admitted amendment set is empty in this release,
so the selected and effective ChangeContract are the base ChangeContract. A
later resolver MAY fold Git-reachable, authority-admitted, digest-chained
amendment Attestations without changing the Lease wire or migrating a Lease.

#### Scenario: A Work Lane is started
- **WHEN** lane start creates a linked worktree and lease
- **THEN** lane start first resolves exactly one active ChangeContract from the
  exact explicitly selected source Work Lane HEAD
- **AND** missing or ambiguous active contracts block before SQLite, ref, or
  worktree effects
- **AND** the clean candidate HEAD contains no active Change carrier
- **AND** the destination is created from candidate, materializes the exact
  selected source carrier in one initialization commit, and contains exactly one
  active Change carrier
- **AND** the initialization commit derives author and committer metadata from
  the exact source HEAD so identical inputs produce the same commit identity
- **AND** the Lease binds lane ref, holder, epoch, the final initialization HEAD,
  and immutable base ChangeContract digest
- **AND** write admission requires exact equality with that digest

#### Scenario: Work Lane start is applied
- **WHEN** `ethos lane start <name> --source-root <source-work-lane> --apply
  --holder-ref <holder-ref>` runs from a clean accepted root and succeeds
- **THEN** ETHOS creates a `work/<name>` linked worktree
- **AND** ETHOS records an active lease in ignored local state under
  `.ethos/state/state.sqlite`
- **AND** raw Git worktree creation is not treated as standard ETHOS workflow
  state because it has no ETHOS lease or verifier-bounded proposition boundary

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --source-root <source-work-lane> --apply
  --holder-ref <holder-ref>` runs from an
  existing `work/*` lane or a dirty accepted root
- **THEN** ETHOS blocks the request with
  `lane_start_requires_clean_accepted_root`

#### Scenario: Source carrier cannot be trusted
- **WHEN** the source root is absent, dirty, from another Git repository, not a
  linked Work Lane, or does not resolve exactly one active ChangeContract at its
  HEAD
- **THEN** lane start blocks before target worktree, ref, commit, or Lease effects
- **AND** it does not infer a carrier from candidate, branch name, archive date,
  or a compatibility alias

#### Scenario: Work Lane is prepared for candidate integration
- **WHEN** `ethos land` evaluates a Work Lane whose exact HEAD still contains
  an active Change carrier
- **THEN** land blocks before candidate ref mutation
- **AND** it directs the operator to the owner-native
  `openspec archive <id> --yes --json` transition
- **AND** candidate, accepted, and release roots remain free of active carriers

#### Scenario: Ref creation loses a compare-and-swap race
- **WHEN** lane start fails to create its ref and observes a same-name ref that
  it did not create
- **THEN** compensation preserves that foreign ref and retains the Lease
- **AND** only a ref whose successful create is proven at the exact final HEAD
  may be compare-and-deleted

### Requirement: Official OpenSpec Lifecycle Adapter
The official OpenSpec CLI SHALL own Change discovery, status, validation, and
archive mutation through `openspec list --json`,
`openspec status --change <id> --json`,
`openspec validate --all --strict --json`, and
`openspec archive <id> --yes --json`. The admitted OpenSpec adapter SHALL consume
those results for `plan`, `prove`, and `land`, and SHALL test archiveability only
in an isolated disposable workspace. It SHALL NOT register or emulate an
OpenSpec command surface.

#### Scenario: Archive closeout gaps block land and closeout
- **GIVEN** owner-native OpenSpec status or strict validation reports an invalid
  active or archived carrier
- **AND** archive metadata or task completion is incomplete
- **WHEN** ETHOS evaluates planning, proof, land, or accepted-root closeout
- **THEN** the exact carrier issue is a required gap
- **AND** the transition remains blocked until owner-native OpenSpec state is
  valid

#### Scenario: Active change fails official archive simulation
- **GIVEN** an active change passes strict validation but owner-native archive
  application would reject its delta against current accepted specs
- **WHEN** ETHOS evaluates the change for proof or land
- **THEN** it runs `openspec archive <id> --yes --json` only in a disposable
  workspace copy
- **AND** returns the official diagnostic code, message, and fix under
  `archive_preflight`
- **AND** reports a change-scoped required gap
- **AND** blocks proof, land, and accepted-root closeout
- **AND** leaves the source OpenSpec workspace unchanged

#### Scenario: Active change passes official archive simulation
- **GIVEN** the disposable owner-native archive application succeeds
- **WHEN** ETHOS records lifecycle readiness
- **THEN** it records a successful isolated preflight
- **AND** it does not archive the source change or mint transition authority
- **AND** any later carrier change requires a new preflight

### Requirement: Lifecycle Review Covers Active Changes
When no Change is explicitly selected, carrier discovery and lifecycle
observation MAY inspect owner-native OpenSpec list and status results for every
active Change. Observation SHALL NOT select a ChangeContract, participate in
material-write coverage, or authorize a write. Planning and proof with multiple
active ChangeContracts SHALL remain ambiguous until an explicit Change selector
is provided. Provider, adopter, and host state SHALL remain bounded to an
adapter, adoption profile, or evidence boundary and SHALL NOT become accepted
capability identity.

#### Scenario: Multiple active changes are reviewed
- **WHEN** carrier discovery or lifecycle observation is requested without a
  Change selector
- **THEN** lifecycle observation includes every active Change returned by
  `openspec list --json`
- **AND** each Change is checked for required carrier files, strict
  ChangeContract validity, accepted `spec.md` identity, exact `subject`, `reuse`,
  and `change` proposal intent, and scope boundaries
- **AND** it does not select a ChangeContract
- **AND** it does not participate in material-write coverage
- **AND** it does not authorize a write
- **AND** multiple active ChangeContracts remain ambiguous until an explicit
  Change selector is provided

### Requirement: Optional tool adapters remain replaceable
Optional environment runners, graph systems, task ledgers, workflow frameworks,
and agent method packs SHALL remain adapter-only boundaries. An adapter MAY
participate only when a current lifecycle command or admitted gate declares it
as a consumer; otherwise it SHALL own no lifecycle truth or required product
surface.

#### Scenario: Adapter profile is reported
- **WHEN** `ethos prove --full --json` compiles a gate that consumes the adapter
- **THEN** proof identifies the adapter boundary and its declared input, output,
  configuration, permission, evidence-artifact, retirement, and truth limits
- **AND** adapter output cannot replace ChangeContracts, owner-native OpenSpec
  state, proof evidence, or Git-native Work Lane semantics

#### Scenario: External workflow frameworks are classified
- **WHEN** ETHOS evaluates an external workflow framework or method pack
- **THEN** only practices consumed by a lifecycle command or admitted gate may
  map to ETHOS contracts, adapters, evidence classes, or projections
- **AND** an unconsumed framework creates no required command, state store, or
  proof surface

### Requirement: Bounded External Evidence Adapters
External identity, hosted-enforcement, independent-verification, and
control-replacement results SHALL enter the kernel only as bounded
`external-assurance` Attestations. Provider-native artifacts remain evidence
references and SHALL NOT create effect Attestation or judgment Attestation entities.

#### Scenario: An external verifier reports a result
- **WHEN** its identity, method, scope, validity interval, and native evidence are
  verifiable
- **THEN** the adapter emits one external-assurance Attestation
- **AND** an unverifiable or stale result resolves to `block` or `unknown`

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires the effect Attestation, verifier executable,
  candidate proof, and bootstrap judgment Attestation to reside outside the
  candidate tree
- **AND** those inputs bind both heads, both control digests, verifier digest,
  proof digest, and bootstrap judgment Attestation digest
- **AND** the candidate proof is a native executed `ethos prove --execute --json`
  result with `command = "prove"`, `ok = true`, `state = "proven"`,
  `data.executed = true`, and matching candidate HEAD bindings in
  `data.evidence.head` and `data.provenance.predicate.head`
- **AND** a hand-authored `{head, state}` envelope is not accepted as candidate
  proof
- **AND** missing or unverifiable provenance returns `defer`.

#### Scenario: Control removal and branch-role changes cannot evade admission

- **WHEN** a candidate changes `.ethos/workspace.toml`, deletes a control path,
  or renames a control path into a non-control location
- **THEN** closeout treats the source control path as changed and requires the
  same candidate-external effect Attestation
- **AND** an unavailable Git diff returns `defer` rather than allowing closeout.

#### Scenario: hosted prevention requires exact receipt

- **WHEN** a protected-ref transition declares hosted prevention
- **THEN** the provider boundary requires a valid signed
  `IndependentVerificationReceipt` before Git accepts the update
- **AND** the effect Attestation exactly binds the remote, proposed commit and tree, action,
  proof-floor ID and digest, gate-policy digest, verifier implementation digest,
  issuer, key ID, validity window, and signature
- **AND** local hooks, provider configuration, or independent re-execution
  without complete hosted mediation do not prove prevention.

#### Scenario: independent re-execution requires an exact signed receipt

- **WHEN** ETHOS projects `independently_reexecuted` for a transition
- **THEN** the provider effect Attestation binds the exact remote, commit, tree, action,
  proof-floor ID and digest, gate-policy digest, verifier implementation digest,
  issuer, key ID, validity window, and signature
- **AND** local hooks or provider configuration alone neither establish
  `independently_reexecuted` nor prove prevention.

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** an operator enables independent verification or generic Git
  pre-receive enforcement
- **THEN** the executable implementation resides outside the ETHOS product
  source and distribution surface
- **AND** it consumes the published provider-neutral effect Attestation contract without
  creating product policy, credentials, accounts, network services, daemons, or
  scheduling requirements.

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** a provider has not installed a conforming generic Git pre-receive
  adapter or its protected provider-local configuration selects `disabled`
- **THEN** ordinary ETHOS adoption, status, plan, prove, land, and local
  publication readiness require no account, key, effect Attestation store, daemon, network
  service, or named service user
- **AND** the adapter does not mint authority or alter product lifecycle truth.

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** a provider-enabled conforming pre-receive adapter receives a
  non-deletion update for a configured protected ref
- **THEN** it accepts the update only when the presented effect Attestation has a
  valid protected-anchor signature and exactly binds the configured remote,
  proposed commit, proposed tree, action, proof-floor ID/digest, gate-policy
  digest, and verifier implementation digest
- **AND** it rejects absent, stale, failed, malformed, unsigned, or mismatched
  effect Attestations before Git accepts the ref.

#### Scenario: An update is outside the configured protected set

- **WHEN** a conforming generic Git pre-receive adapter receives an update for a
  ref not named by its provider-local protected-ref configuration
- **THEN** it does not require an effect Attestation for that ref
- **AND** it does not execute a client-supplied command or infer policy from the
  proposed tree.

#### Scenario: The server adapter remains a thin physical extension

- **WHEN** GitHub, GitLab, independent-identity, or generic Git providers project
  external enforcement
- **THEN** they conform to the same effect Attestation and judgment Attestation contract
- **AND** no provider executable becomes a second governance kernel or a
  required ETHOS distribution asset.

### Requirement: Exact-request Mutation Admission
Mutation admission SHALL compile a transient exact-request PlanIR from the
selected ChangeContract, fresh RepositoryFacts, and prior Attestations. Routine
local coordination returns only an ignored local postcondition receipt;
repository-semantic exceptional or irreversible mutation emits the corresponding
effect Attestation rather than a separate model or lifecycle owner.

#### Scenario: Apply mode is requested
- **WHEN** land or publish requests a guarded effect
- **THEN** explicit confirmation and the expected HEAD are required before
  mutation
- **AND** action, resource, expected state, policy refs, evidence refs, and
  decision basis are evaluated for that request only
- **AND** no role, token, session, exception, or reusable permission is minted

### Requirement: Intake Adapter Projection Boundary
Intake and backlog providers SHALL contribute fresh RepositoryFacts or
observation Attestations only when consumed by a selected ChangeContract. Their
state SHALL NOT close, promote, or retire lifecycle truth.

#### Scenario: Intake provider reports done state
- **WHEN** an intake provider reports a task as complete
- **THEN** ETHOS records only bounded projection evidence
- **AND** trust closeout still requires a selected ChangeContract, its required
  Attestations, owner-native OpenSpec lifecycle readiness, and executed proof
- **AND** intake state does not select targets, close, promote, retire, or
  authorize lifecycle truth

## REMOVED Requirements

### Requirement: Work Lane Claim Binding Projection

**Reason**: The accepted form assigns durable semantic ownership to a retired model or binds operational truth to that model.

**Migration**: Terminal Adapter Compilation And Evidence absorbs every scenario through the selected base ChangeContract, fresh RepositoryFacts, transient PlanIR, and verifier-bounded Attestations; history remains a derived projection.

**Replacement**: Terminal Adapter Compilation And Evidence

**Scenario replacement**: Work Lane has a claim binding -> Work Lane has a valid base-bound Lease

**Scenario replacement**: Work Lane lacks a claim binding -> Work Lane Lease is unverifiable or absent
