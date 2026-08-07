## MODIFIED Requirements

### Requirement: Exact-request Mutation Admission
Only a `pass` verdict may authorize an effect; `block` and `unknown` both fail closed.

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

#### Scenario: multiple hooks can observe one mutation
- **WHEN** an optional tool proposes another mutation hook or guard
- **THEN** one authoritative ETHOS guard remains the sole mutation admission path
- **AND** the optional tool cannot install a second hook, bypass, or state owner

#### Scenario: refresh-base CAS fails after local rebase

- **WHEN** the candidate rebase has detached a Work Lane checkout but the exact ref or Lease CAS
  is rejected
- **THEN** ETHOS SHALL compensate the checkout to the original branch, HEAD, index, and worktree
  before returning a blocked verdict
- **AND** a failed command SHALL leave no detached partial target state.

### Requirement: Bounded External Evidence Adapters
A successful effect SHALL be followed by fresh observation and an Attestation binding the Commitment, Facts, policy, TransitionPlan, effect, and resulting artifact. Historical re-evaluation is non-authorizing analysis only.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires the receipt, verifier executable, candidate proof,
  and bootstrap Attestation to reside outside the candidate tree and bind
  both heads, both control digests, verifier digest, proof digest, and bootstrap
  Attestation digest
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

#### Scenario: historical carriers can no longer be parsed
- **WHEN** a historical OpenSpec or policy layout has changed
- **THEN** an already issued Attestation remains verifiable through its bindings
- **AND** admission does not re-run the historical workflow to authorize a new effect

### Requirement: Official OpenSpec Lifecycle Adapter
The official OpenSpec CLI SHALL own Change identity, design, specs,
task-progress, artifact dependencies, and archive lifecycle for every complete
mutation-capable adopter. Generic kernel compilation SHALL not import OpenSpec types.

#### Scenario: official active state is malformed or ambiguous

- **WHEN** official `list --json` has an invalid wire shape, an absent explicitly
  requested Change, or multiple implicitly selectable Changes
- **THEN** ETHOS blocks with a precise gap
- **AND** it does not select by timestamp, directory order, task-file parsing,
  fallback field names, or a private rank.

#### Scenario: A complete adopter selects a custom workflow schema
- **WHEN** project configuration or Change metadata resolves a valid built-in,
  project-local, or installed OpenSpec schema
- **THEN** ETHOS uses the official resolved schema name, artifact IDs, dependency
  graph, output paths, templates, and apply prerequisites
- **AND** fresh Change creation does not force `spec-driven` or fixed
  `proposal`, `specs`, `design`, and `tasks` rule keys
- **AND** official schema validation and runtime status remain the structural
  authority rather than an ETHOS parser or community-schema claim

#### Scenario: A community schema claims additional enforcement
- **WHEN** a community workflow adds reviews, ADRs, tests, retrospectives,
  Gherkin formats, human gates, or external skills
- **THEN** ETHOS distinguishes artifact-DAG enforcement from prompt-only
  convention, external runtime dependency, and unknown keys ignored by OpenSpec
- **AND** only independently verified mechanisms with one owner and net deletion
  may be absorbed into the selected project schema

#### Scenario: ETHOS observes an active OpenSpec carrier
- **WHEN** the self profile evaluates current OpenSpec state
- **THEN** the adapter consumes official `doctor`, `list`, `status`, and strict
  `validate` observations
- **AND** malformed list structure, unknown status, an absent explicit Change,
  or ambiguous implicit selection blocks instead of becoming an empty clean list
- **AND** no reader, plan, or proof path invokes or predicts `archive`.

#### Scenario: a completed Change remains active
- **WHEN** official `list` reports a completed Change under the active changes
  surface
- **THEN** land and accepted-root closeout report
  `openspec_completed_change_unarchived:<change>`
- **AND** the gap clears only after the owner-native archive operation removes
  that Change from official active state.

#### Scenario: historical archives use an older shape

- **WHEN** a historical archive contains obsolete names, metadata, tasks, or
  delta layout
- **THEN** ETHOS preserves it as non-authorizing history
- **AND** current admission does not re-run or reinterpret that historical
  workflow.

#### Scenario: Historical archive bytes use an older shape
- **WHEN** a historical archive has obsolete naming, metadata, tasks, or delta
  layout
- **THEN** ETHOS does not re-run or reinterpret that historical workflow to
  authorize or block a current effect
- **AND** already issued Attestations remain verifiable through their exact
  bindings.

#### Scenario: ETHOS archives its own active change
- **WHEN** the self profile selects OpenSpec and the Change is ready for archival
- **THEN** `ethos lane archive-change --change <id> --expect-head <head>
  --apply` verifies the same-holder Lease, exact HEAD/tree, completed official
  status, strict validation, and HEAD-bound proof before invoking pinned
  OpenSpec `1.8.0`
- **AND** the command admits only the exact source-to-archive rename and canonical
  spec delta, commits it through normal hooks, advances the Lease to the archived
  Commitment, and emits a content-addressed typed Attestation
- **AND** stale facts, foreign holders, changed output, replay, or ref drift fail
  closed without leaving a partial archive
- **AND** the resulting archive is history, not a generic runtime authority

### Requirement: Optional tool adapters remain replaceable
ETHOS SHALL use admitted mature capabilities directly and reject a framework, generator, plugin layer, DI container, or event bus without a concrete consumer, conformance proof, uninstall cleanliness, and net deletion.

#### Scenario: Adapter profile is reported

- **WHEN** `ethos prove --gate product-boundary --json` reports tool adapters
- **THEN** Nox, Pixi, Pants, task-ledger, and agent-method-pack entries SHALL be
  visible as adapter-only boundaries
- **AND** their output SHALL NOT replace ETHOS proof, OpenSpec lifecycle checks,
  Attestations, evidence, or Git-native Work Lane semantics.

#### Scenario: External workflow frameworks are classified
- **WHEN** ETHOS evaluates COMET, Spec Kit, BMAD, Superpowers, Task Master, Agent OS, OpenSPDD, Shotgun, or fspec
- **THEN** their useful practices may be mapped to ETHOS contracts, adapters, evidence classes, projections, or method packs
- **AND** their command planes, hidden state directories, task stores, and phase names do not become ETHOS lifecycle truth by default

#### Scenario: COMET participates in evaluation or external operation
- **WHEN** COMET is used as a benchmark treatment or optional external operator
- **THEN** Native, Classic, archive, state machine, hooks, dashboard, Bundle,
  marketplace, adapter, provider, and state-reader implementations remain outside ETHOS
- **AND** COMET output enters only as untrusted observation and requires an ETHOS
  verifier before it can become an Attestation
- **AND** COMET cannot decide `done`, land, publish, or OpenSpec archive

#### Scenario: a single implementation requests a plugin framework
- **WHEN** no independent consumer needs substitution
- **THEN** explicit composition remains the implementation
