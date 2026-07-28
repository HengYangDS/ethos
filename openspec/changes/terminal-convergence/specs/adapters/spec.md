## MODIFIED Requirements

### Requirement: Exact-request Mutation Admission
An adapter SHALL observe external state or execute a compiled effect under exact permissions and preconditions. It SHALL not own repository truth, currentness, or hidden workflow state.

#### Scenario: Apply mode is requested
- **WHEN** `ethos land --apply` or `ethos publish --apply` runs
- **THEN** ETHOS requires explicit confirmation and expected HEAD before any
  mutation can proceed
- **AND** the decision binds action, resource, expected state, policy refs,
  evidence refs, and decision basis
- **AND** it mints no role, token, session, or reusable permission.

#### Scenario: an adapter requests a mutation
- **WHEN** its requested effect is absent from the TransitionPlan or its CAS precondition no longer matches
- **THEN** ETHOS blocks before invoking the adapter

### Requirement: Bounded External Evidence Adapters
A successful effect SHALL be followed by fresh observation and an Attestation binding the Commitment, Facts, policy, TransitionPlan, effect, and resulting artifact. Historical re-evaluation is non-authorizing analysis only.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires the receipt, verifier executable, candidate proof,
  and bootstrap Chronicle decision to reside outside the candidate tree and bind
  both heads, both control digests, verifier digest, proof digest, and bootstrap
  decision digest
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
  same candidate-external receipt
- **AND** an unavailable Git diff returns `defer` rather than allowing closeout.

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

#### Scenario: historical carriers can no longer be parsed
- **WHEN** a historical OpenSpec or policy layout has changed
- **THEN** an already closed Attestation remains verifiable through its bindings
- **AND** admission does not re-run the historical workflow to authorize a new effect

### Requirement: Official OpenSpec Lifecycle Adapter
The official OpenSpec CLI SHALL own validation and archival for ETHOS's selected self-profile carrier. Generic adapter compilation SHALL not import or require OpenSpec.

#### Scenario: Archive closeout gaps block land and closeout

- **GIVEN** official OpenSpec list status has no completed active changes
- **AND** an archived change is missing archive metadata or has incomplete tasks
- **WHEN** ETHOS evaluates OpenSpec lifecycle closeout for land or accepted-root
  closeout
- **THEN** ETHOS reports the archive issue as a required gap
- **AND** land or closeout remains blocked until archive state is repaired.

#### Scenario: Active change fails official archive simulation

- **GIVEN** an active change is syntactically valid but the configured official
  OpenSpec archive command would reject its delta against the current canonical
  specs
- **WHEN** ETHOS evaluates OpenSpec lifecycle for the change
- **THEN** ETHOS runs the official archive only in a disposable workspace copy
- **AND** returns the official diagnostic code, message, and fix under the
  change's `archive_preflight` data
- **AND** reports a change-scoped required gap
- **AND** proof, land, and accepted-root closeout remain blocked
- **AND** the source OpenSpec workspace remains unchanged.

#### Scenario: Active change passes official archive simulation

- **GIVEN** an active change's official archive simulation succeeds
- **WHEN** ETHOS evaluates OpenSpec lifecycle for the change
- **THEN** lifecycle records a successful isolated preflight
- **AND** it does not archive the source change, complete tasks, or mint
  authority
- **AND** a later source change requires lifecycle to evaluate archiveability
  again.

#### Scenario: ETHOS archives its own active change
- **WHEN** the self profile selects OpenSpec and archiveability is attested
- **THEN** ETHOS invokes the owner-native OpenSpec operation
- **AND** the resulting archive is history, not a generic runtime authority

### Requirement: Optional tool adapters remain replaceable
ETHOS SHALL use admitted mature capabilities directly and reject a framework, generator, plugin layer, DI container, or event bus without a concrete consumer, conformance proof, uninstall cleanliness, and net deletion.

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

#### Scenario: a single implementation requests a plugin framework
- **WHEN** no independent consumer needs substitution
- **THEN** explicit composition remains the implementation
