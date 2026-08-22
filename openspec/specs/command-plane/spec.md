# ETHOS Command Plane

## Purpose

ETHOS SHALL expose the public command plane without owning repository lifecycle
semantics.

## Requirements

### Requirement: Public Command Plane
ETHOS SHALL keep the normal user workflow under six public commands:
`ethos adopt`, `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. Accepted-head admission is an exact `ethos land --closeout`
operation, not a seventh top-level command or a hidden Git-hook procedure.

#### Scenario: Cyclopts exposes the terminal root surface
- **WHEN** the root CLI help is rendered
- **THEN** it exposes exactly the six public commands
- **AND** `ethos status` is the single bounded reader
- **AND** maintainer mechanics remain hidden or semantically namespaced

#### Scenario: TransitionPlan is the single transition projection
- **WHEN** `ethos plan --json` compiles the current Commitment, repository
  facts, and declared nodes
- **THEN** it returns one deterministic `transition_plan`
- **AND** no parallel workflow-runtime or domain-contract read model is emitted

#### Scenario: Default payloads stay bounded
- **WHEN** `ethos status --json` or `ethos plan --json` would exceed its declared
  default payload budget
- **THEN** the command preserves `verdict`, `state`, `summary`, `required_gaps`,
  `next_action`, `continuation`, `missing_facts_or_evidence`, and
  `user_decision_required`
- **AND** oversized detail is replaced by a digest-bound artifact reference
- **AND** no alternate reader command or truth source is introduced

#### Scenario: a reader derives continuation
- **WHEN** current authoritative facts are sufficient to select the next boundary
- **THEN** the schema-version-`2` result preserves `state` and `required_gaps`,
  exposes one `next_action`, and derives exactly one `continuation`: `continue`,
  `await-user`, `blocked`, or `done`
- **AND** `missing_facts_or_evidence` derives from `required_gaps` only when
  `verdict=unknown`, while `user_decision_required` names required judgment
- **AND** Continuation is recomputed rather than stored as lifecycle truth

#### Scenario: accepted closeout remediation is directly executable
- **WHEN** accepted-head admission is blocked by missing proof, missing external
  verification, stale coordinates, or an unapplied exact effect
- **THEN** status, plan, land, and hook projections SHALL expose the same single
  complete `ethos ...` command
- **AND** that command SHALL bind the current root, expected accepted HEAD,
  candidate HEAD, and any required receipt path
- **AND** it SHALL contain no prose-only instruction or placeholder token.

### Requirement: Cyclopts And API Own Interface Semantics
Concrete Cyclopts declarations and the in-process operation API SHALL own command
names, parameters, help, and dispatch. ETHOS SHALL NOT maintain a parallel command
registry, lazy report-handler DSL, re-export facade, or command-shaped quality
plane.

#### Scenario: A command signature changes
- **WHEN** a public operation changes its parameters or help
- **THEN** CLI, SDK metadata, generated docs, and protocol projections derive from
  the same operation declaration
- **AND** no tracked command declaration must be synchronized by hand

#### Scenario: ETHOS runs from an installed wheel
- **WHEN** the package runs outside a source checkout
- **THEN** packaged lifecycle and gate resources remain available
- **AND** command discovery still comes from Cyclopts declarations, not a packaged
  command registry

### Requirement: Prove Is The Singular Quality Execution Surface
Quality checks SHALL be selected by gate ID through `ethos prove --gate <gate-id>`.
`system/gates.toml` SHALL bind each gate to concrete Python providers or an external
owner command without looping back through another ETHOS command.

#### Scenario: One focused gate is requested
- **WHEN** `ethos prove --execute --gate <gate-id> --json` runs
- **THEN** the declared provider or external adapter executes directly
- **AND** the proof evidence records the gate ID, adapter identity, verdict, and
  diagnostics
- **AND** no `ethos quality` command is registered or invoked

### Requirement: CLI Surface Delegation
The CLI SHALL compose output and UX while delegating semantics to contracts,
operations, repository policy, and adapters.

#### Scenario: CLI package is scanned
- **WHEN** architecture tests inspect imports
- **THEN** command modules call concrete operation and adapter owners
- **AND** no command registry, generic report compiler, or CLI subprocess loopback
  exists

### Requirement: Retired Family Command Vocabulary
ETHOS SHALL reject retired family-style command prefixes from governed docs.

#### Scenario: Retired capability command appears
- **WHEN** governed docs contain `ethos governance`, `ethos workspace`,
  `ethos agent`, `ethos project`, `ethos kernel`, or `ethos node` as a command
- **THEN** the command-surface and documentation gates report a required gap

### Requirement: Proof Command State Semantics
The public result envelope has no top-level `ok` field; `verdict` is the sole public authorization result.

ETHOS CLI SHALL present proof command states according to execution depth.

#### Scenario: Planning proof is ready
- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `verdict=pass` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven
- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `verdict=pass` and `state=proven`
- **AND** the CLI reports `executed=true`

### Requirement: Self OpenSpec Lifecycle Mode
ETHOS CLI SHALL expose OpenSpec lifecycle review through the public ETHOS
command plane.

#### Scenario: OpenSpec lifecycle is audited
- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the CLI reports official OpenSpec validation and ETHOS lifecycle
  carrier readiness in one result envelope

### Requirement: ETHOS OpenSpec adapter remains under one command plane
ETHOS SHALL expose OpenSpec governance health through `ethos openspec --json`
and `ethos openspec --lifecycle --json` while keeping the public workflow
centered on `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`.

#### Scenario: OpenSpec adapter composes official and ETHOS checks
- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the payload includes official OpenSpec doctor, status, and strict
  validation results
- **AND** it includes ETHOS lifecycle carrier review for proposal, design,
  tasks, delta specs, capability profiles, Commitment validity, evidence refs, and
  live-spec diff guards

#### Scenario: OpenSpec adapter does not become a second public command plane
- **WHEN** ETHOS reports OpenSpec governance gaps
- **THEN** the next action enters through an `ethos ...` command
- **AND** raw OpenSpec CLI commands remain adapter implementation detail or
  maintainer reference rather than the adopter first-hour workflow

#### Scenario: Lifecycle semantics use OpenSpec as carrier
- **WHEN** lifecycle or transition semantics are changed
- **THEN** an OpenSpec change carrier records the intent and deltas
- **AND** official OpenSpec validation remains carrier validation rather than runtime authority

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose `ethos explain` as a read-only invalid-state taxonomy
projection for governance gaps and advisory signals.

#### Scenario: Explain accepts advisory signals without required-gap overclaim

- **WHEN** `ethos explain <signal> --json` runs for a non-blocking advisory signal
- **THEN** the payload keeps the original string as `gap` for the stable result contract
- **AND** the payload also exposes the original string as `signal`
- **AND** the payload classifies the signal into an invalid-state category
- **AND** the payload wording does not claim every explained signal is a required gap
- **AND** the taxonomy projection does not become a lifecycle command

#### Scenario: Explain help and docs use gap-or-signal language

- **WHEN** a human or agent reads `ethos explain --help` or the command-plane reference
- **THEN** the command is described as explaining a governance gap or advisory signal
- **AND** docs show `ethos explain <gap-or-signal>` rather than a required-gap-only surface
- **AND** the command remains a read-only projection, not a lifecycle command

### Requirement: Governed transition commands fail closed on blocking verdicts

ETHOS transition commands that gate proof, land, or publish SHALL expose blocking
verdicts through both command JSON and non-zero process exit status unless the
command is explicitly documented as a read-only reader view.

#### Scenario: gapped proof refuses through process status

- **WHEN** `ethos prove --expect-head <non-current-head> --json` runs
- **THEN** the JSON payload reports `verdict=block`
- **AND** the payload includes `expected_head_mismatch` in `required_gaps`
- **AND** the process exits with non-zero status

### Requirement: Protected roots are observe-only by default

Protected-root shell pre-run admission SHALL deny unknown mutation-capable
commands unless the command is explicitly classified as read-only or binds its
tracked paths through prewrite admission.

#### Scenario: unknown shell command targets a protected root

- **WHEN** a shell pre-run check sees an unclassified command in an accepted,
  candidate, or release root without bound paths
- **THEN** ETHOS blocks the command as protected-root mutation risk
- **AND** the caller must route the change through an owned Work Lane and
  `ethos lane prewrite`

### Requirement: Work Lane writes are exact lease-generation bound

Tracked Work Lane writes SHALL require an active Work Lane lease and an
invocation holder reference matching the exact holder, lease ID, epoch, and
expected HEAD.

#### Scenario: invocation binding is stale or foreign

- **WHEN** `ethos lane prewrite` runs with a different holder, lease ID, epoch,
  or HEAD than the current lease
- **THEN** the report blocks the write with the corresponding exact-binding gap
- **AND** visibility of the Work Lane does not authorize write, land, retire, or
  cleanup

### Requirement: Semantic Lane Lifecycle Groups

ETHOS SHALL group lease, handoff, exceptional resolution, and retirement under
semantic nested command families.

#### Scenario: retirement commands are grouped

- **WHEN** maintainers inspect the Lane command plane
- **THEN** bounded retirement commands are `ethos lane retire landed`,
  `ethos lane retire superseded`, `ethos lane retire unbound`, and
  `ethos lane retire reconcile-ref-absent`
- **AND** lease lifecycle is under `ethos lane lease`, handoff under
  `ethos lane handoff`, and exceptional judgment under `ethos lane resolution`.

### Requirement: Candidate ref movement is proof-bound

Candidate ref movement SHALL be protected by executed proof bound to the new
candidate head, just like accepted-root closeout.

#### Scenario: raw candidate ref update lacks executed proof

- **WHEN** a ref update attempts to move `candidate/dev` without sanctioned ETHOS
  land semantics and executed proof for the new head
- **THEN** the reference-transaction admission blocks the ref movement
- **AND** sanctioned land may proceed only through the explicit ETHOS ref-move
  allowance after its own proof checks

#### Scenario: official candidate refresh carries scoped ref-move context

- **WHEN** `ethos lane candidate --refresh-from-accepted --apply --authorize`
  resets a clean candidate worktree to the accepted root under an armed
  reference-transaction hook
- **THEN** the reset carries the scoped official ref-move allowance
- **AND** the command still requires `--expect-head` and reports
  `candidate_refresh_from_accepted_failed` if the reset fails

### Requirement: Publish reports local readiness without remote publication

`ethos publish` SHALL report local publish readiness and deferred remote
publication as separate facts, using current state vocabulary only.

#### Scenario: local publish readiness is available but remote push is deferred

- **WHEN** `ethos publish --json` runs without applying a remote push
- **THEN** the state is `local_publish_ready` when local gates are satisfied
- **AND** `remote_push` is `not_performed`
- **AND** hosted CI success is not claimed
- **AND** the payload does not expose retired publish-state vocabulary

### Requirement: OpenSpec archive query uses logical Change IDs

ETHOS SHALL expose an explicit read-only archive query that accepts a date-free
lower-kebab logical OpenSpec Change ID beginning with a letter, and resolves
exactly one `YYYY-MM-DD-<logical-id>` archived carrier under
`openspec/changes/archive` without mutating historical archives. A terminal
`YYYYMMDD` segment is not part of a logical Change ID.

#### Scenario: Logical archive ID resolves uniquely

- **WHEN** `ethos openspec --archive-id <logical-id> --json` receives a valid
  logical ID with exactly one matching `YYYY-MM-DD-<logical-id>` archive
- **THEN** it reports `state=resolved` and the relative archive carrier path
- **AND** it does not invoke an active Change status lookup or archive mutation

#### Scenario: Archive query fails closed

- **WHEN** an archive query receives an invalid logical ID, an archive directory
  name, no matching archive, or more than one matching archive
- **THEN** it reports a distinct required gap for that condition
- **AND** it does not choose an archive by date or mutate an archive

#### Scenario: Numeric or temporal logical IDs are rejected

- **WHEN** an archive query receives a numeric-leading ID, terminal-date ID,
  archive directory name, absent ID, or ambiguous logical ID
- **THEN** ETHOS SHALL reject it as an invalid logical Change ID
- **AND** it SHALL require the date-free logical ID rather than an alias, redirect, or fallback lookup.

### Requirement: Active Change selection excludes archive directory names
ETHOS SHALL keep `ethos openspec --change` scoped to active logical Change IDs.

#### Scenario: Archive directory is passed to active selector
- **WHEN** `ethos openspec --change` receives the exact name of an archived
  `YYYY-MM-DD-<logical-id>` directory
- **THEN** it reports `openspec_active_change_identifier_is_archive_directory:<name>`
- **AND** it does not treat the archived carrier as an active Change

### Requirement: Commitment rebind coordinates are publicly derived

ETHOS SHALL provide a read-only derive operation that converts the current
owned Work Lane observations and one exact compatible signed target commit into
a digest-bound Commitment-rebind request receipt.

#### Scenario: Exact target is derived

- **GIVEN** one valid Lease is held by the invocation actor and exactly one
  signed dangling target commit represents the staged Commitment transition
- **WHEN** rebind derivation runs
- **THEN** ETHOS returns the old and new carrier paths, bytes digests, semantic
  digests, HEAD, tree, index, overlay, Lease generation, target OID, receipt
  path, and receipt digest
- **AND** the caller supplies business intent rather than copying those internal
  coordinates.

#### Scenario: Target derivation is ambiguous

- **WHEN** zero or more than one compatible signed target is observable
- **THEN** derivation blocks without selecting one
- **AND** it reports the observed candidate OIDs and the unique public next
  command when a mechanical next step exists.

### Requirement: Commitment rebind apply consumes an exact receipt

ETHOS SHALL allow rebind dry-run and apply to consume a derive receipt and SHALL
revalidate all mutable coordinates before effect execution.

#### Scenario: Unchanged receipt applies

- **WHEN** receipt-bound apply observes the same holder, Lease generation, HEAD,
  tree, index, overlay, target commit, signature trust, and carrier semantics
- **THEN** the existing exact Git and Lease transaction applies
- **AND** the terminal receipt binds the derive receipt digest and all effects.

#### Scenario: Any coordinate drift fails closed

- **WHEN** any receipt-bound coordinate changes before dry-run or apply
- **THEN** ETHOS reports a typed `missing`, `mismatch`, `stale`, `drift`, or
  `authority_denied` blocker naming observed and expected values
- **AND** no Git ref or Lease effect is applied.

### Requirement: Commitment rebind failures are directly actionable

ETHOS SHALL recognize an active Commitment transition as a dedicated lifecycle
condition and project one typed remediation rather than a generic ref or bytes
mismatch.

#### Scenario: Normal commit creates a valid dangling target

- **WHEN** hook admission prevents the Work Lane ref from advancing because the
  active Commitment changed but the signed target object was created
- **THEN** ETHOS reports `commitment_rebind_required`
- **AND** it returns the valid target OID, old and new carrier digests, partial
  effects, and the one copy-safe derive command
- **AND** it tells the caller not to repeat the commit.

#### Scenario: Structured remediation remains bounded

- **WHEN** a lifecycle blocker is emitted
- **THEN** its remediation identifies the owner, reason, observed and expected
  values, whether mutation or user decision is required, retryability, and one
  existing public next command
- **AND** full diagnostics remain available through an immutable artifact
  reference rather than an unbounded default payload.

### Requirement: Attestation record and query project one set contract

The public command plane SHALL expose one narrow record/query surface over the
Attestation set. Record SHALL issue from explicit canonical input or validate an
existing Attestation, then exact-CAS union it. Query SHALL filter the selected set
by exact semantic fields without creating selection, workflow, or task state.

#### Scenario: An input occurrence is recorded

- **WHEN** explicit source occurrence coordinates, predicate, subject, verifier,
  payload, relations, and bindings are valid
- **THEN** the command issues one canonical Attestation and adds it idempotently
- **AND** structured output returns set root and Attestation identity

#### Scenario: Unknown input is queried

- **WHEN** its payload or relation kind is not understood by an effect evaluator
- **THEN** query returns the preserved canonical value
- **AND** no command projection describes it as authoritative

### Requirement: Lifecycle commit objects inherit repository signing policy

ETHOS SHALL create direct lifecycle commit objects through one owner that
inherits the repository's effective commit-signing policy and verifies any
required signature before a ref or Lease effect.

#### Scenario: Signing is enabled and trusted

- **WHEN** a lifecycle operation creates a commit object in a repository whose
  effective `commit.gpgsign` is enabled
- **THEN** the object is signed with the bound configured signer
- **AND** external trust verification passes before any ref mutation.

#### Scenario: Signing is disabled

- **WHEN** effective `commit.gpgsign` is disabled or absent
- **THEN** the lifecycle object may remain unsigned
- **AND** ETHOS does not invent a repository-independent signing requirement.

#### Scenario: Required signature is not trusted

- **WHEN** signing is enabled but object creation or external trust verification
  fails
- **THEN** the lifecycle operation reports the typed signing gap
- **AND** no ref, Lease, or worktree effect remains.

### Requirement: Publish is the sole remote Git object projection command

`ethos publish` SHALL be the sole public command that compiles, persists, and
applies remote Git object effects. It SHALL select typed targets from the
repository's positive ref topology, bind the exact local object and proof
Attestation, persist one content-addressed request, recheck every target before
the first effect, execute peer-local exact CAS, and emit one machine-readable
partial or complete Attestation. Tag publication and protected-branch
publication SHALL be modes of this command rather than separate commands or
hook exceptions.

#### Scenario: dry-run creates one immutable request

- **WHEN** a caller requests remote projection with exact local and peer facts
- **THEN** `ethos publish` SHALL return the request path, digest, source object, targets, proof, and exact apply command
- **AND** it SHALL perform no remote mutation

#### Scenario: apply consumes the same request

- **WHEN** request bytes and all bound coordinates remain current
- **THEN** `ethos publish --receipt ... --apply --authorize` SHALL execute only the request's effects
- **AND** it SHALL reject any repository, object, proof, ref, peer, or expected-OID drift

#### Scenario: missing proof is actionable

- **WHEN** the selected local object lacks the required exact proof Attestation
- **THEN** publish and pre-push SHALL report the same proof gap
- **AND** both SHALL identify `ethos prove --execute --expect-head <oid> --json` as the sole continuation

### Requirement: Hook runtime inspection exposes one exact repair action
The existing hook runtime and status projections SHALL report installed source
identity, expected source identity, currentness, and one deterministic repair
command without requiring digest archaeology.

#### Scenario: stale runtime is observed in an ETHOS repository family
- **WHEN** the installed runtime identity differs from the accepted ETHOS ref identity
- **THEN** the result reports both source commit/tree pairs and the stale-source gap
- **AND** `next_action` is a complete copyable command bound to the current worktree and accepted source checkout

#### Scenario: stale runtime is observed by a package-only installation
- **WHEN** no ETHOS source checkout supplies the runner
- **THEN** expected identity comes from the invoking wheel's immutable build identity
- **AND** `next_action` repairs the current worktree through the existing `ethos hook install` command

#### Scenario: repair completes
- **WHEN** hook installation post-observes a current runtime
- **THEN** the result reports `verdict=pass` with no repair action
- **AND** status, JSON, and hook inspection consume the same runtime binding rather than deriving separate remedies
