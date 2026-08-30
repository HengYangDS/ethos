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

The public result envelope has no top-level `ok` field; `verdict` is the sole
public authorization result.

`ethos prove` SHALL distinguish readiness, exact execution, and recoverable
lifecycle-plan failure while projecting one command owned by the responsible
transition.

#### Scenario: Planning proof is ready

- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `verdict=pass` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven

- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `verdict=pass` and `state=proven`
- **AND** the CLI reports `executed=true`

#### Scenario: Exact committed archive leaves a stale Lease

- **WHEN** proof planning observes a stale Work Lane Lease whose current HEAD is
  the exact recoverable archive post-image
- **THEN** proof blocks with the stale-Lease gap
- **AND** `next_action` is the exact `ethos lane archive-change` command bound to
  the Change and Lease expected HEAD
- **AND** it does not direct the operator to repository adoption.

#### Scenario: Other stale Lease state remains non-destructive

- **WHEN** proof planning observes Lease staleness that is not an exact archive
  post-image
- **THEN** proof directs the operator to `ethos lane status --json`
- **AND** it does not infer archive recovery or adoption authority.

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

ETHOS SHALL group Lease, handoff, retirement, and archive transitions under the
single `ethos lane` command family. Official Change creation and artifact
completion SHALL remain owned by the OpenSpec command plane; ETHOS SHALL NOT
advertise a parallel Change-authoring command or intent carrier.

#### Scenario: Lane lifecycle commands are grouped

- **WHEN** maintainers inspect `ethos lane --help`
- **THEN** linked retirement is exposed by `ethos lane retire landed` and
  `ethos lane retire superseded`
- **AND** exact absorbed unbound-ref retirement is exposed only by
  `ethos lane retire absorbed-ref`
- **AND** Lease lifecycle, handoff, and archive remain under
  `ethos lane lease`, `ethos lane handoff`, and `ethos lane archive-change`
- **AND** official Change creation and artifact completion remain owned by the
  OpenSpec command plane

#### Scenario: A Work Lane has no active Change

- **WHEN** current resolution observes an owned Work Lane with no active official Change
- **THEN** the single next action is the exact official `openspec new change <id>` command when the identifier is supplied by the caller
- **AND** ETHOS does not synthesize proposal, spec, design, task, scope, lineage, or Commitment files

#### Scenario: An active Change is incomplete

- **WHEN** the selected official Change reports its next ready artifact
- **THEN** the single next action names the corresponding official OpenSpec instructions command
- **AND** the machine gap preserves the exact incomplete artifact boundary

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

### Requirement: Hook installation reports repository-family convergence

`ethos hook install` SHALL project one Git-common activation operation rather
than only the invoking worktree.

#### Scenario: Installation converges linked worktrees

- **WHEN** hook installation succeeds from any linked worktree
- **THEN** JSON reports the effective common hooks path and immutable runtime identity
- **AND** it lists every linked worktree as checked or repaired
- **AND** it lists exact checked, removed, and retained generated paths
- **AND** `next_action` is empty because no further repair is required.

#### Scenario: Installation cannot establish convergence

- **WHEN** a linked worktree or generation consumer cannot be observed exactly
- **THEN** installation returns a non-pass verdict before deleting a generated path
- **AND** `next_action` is the complete root-bound `ethos hook install` command.

### Requirement: Public version inspection exposes immutable provenance
ETHOS SHALL provide one public version inspection path whose human and JSON
projections are derived from the same identity result.

#### Scenario: Human version is requested
- **WHEN** a user runs `ethos --version`
- **THEN** ETHOS prints a concise product and distribution identity
- **AND** it does not serialize a JSON document inside a string.

#### Scenario: Machine version is requested
- **WHEN** an agent runs `ethos --version --json`
- **THEN** stdout is one valid UTF-8 JSON document containing product version,
  distribution version, source commit/tree, wheel SHA256 or explicit absence,
  and runtime digest or explicit absence
- **AND** JSON string escaping is used only where required by JSON syntax.

### Requirement: Command results use one closed semantic envelope

Every public command result SHALL carry one authoritative, self-explanatory
verdict. `pass` SHALL carry no blocker; `unknown` SHALL name missing facts or
evidence; `block` SHALL name a failed condition or adverse diagnostic. A
projection SHALL NOT manufacture a verdict from facts-only data.

#### Scenario: Required facts are unavailable

- **WHEN** a required fact or evidence item is unavailable
- **THEN** the verdict is `unknown` and `required_gaps` names it.

#### Scenario: A condition blocks the operation

- **WHEN** an admitted precondition fails
- **THEN** the verdict is `block` with a named gap or adverse diagnostic.

#### Scenario: Work Lane validation is healthy

- **WHEN** workspace validation passes
- **THEN** `lane status` is `pass`; coordination advisories stay observations.

### Requirement: Current Work Lane authority has one fresh resolver

ETHOS SHALL resolve tracked-write authority from the current worktree, branch
role, invocation actor, and exact four-field Lease. It SHALL read HEAD, tree,
index, changed paths, and official OpenSpec intent as fresh facts. Historical
transition Attestations SHALL provide provenance only and SHALL NOT mint,
revoke, or replace current authority.

#### Scenario: Current binding is exact without historical transition evidence

- **GIVEN** the invocation actor owns a valid Lease for the current Work Lane
- **AND** the current checkout has one valid active official OpenSpec Change
- **WHEN** status, plan, prewrite, or pre-commit resolves authority
- **THEN** every surface projects the same passing Lease and fresh repository facts
- **AND** no carrier, rebind, or historical effect record is required

#### Scenario: Current binding is stale or ambiguous

- **WHEN** the actor, Lease generation, branch role, Git facts, or selected official Change is missing or ambiguous
- **THEN** every consuming surface fails closed with the same first exact reason
- **AND** historical transition evidence cannot override the mismatch

#### Scenario: Historical transition evidence remains provenance

- **WHEN** valid transition Attestations are available
- **THEN** path attribution and effect verification may cite them
- **AND** removing them changes provenance detail only, not a valid current authoring verdict

### Requirement: Current repository decisions have one resolution owner

ETHOS SHALL resolve current role, actor, Lease, fresh Git facts, selected
official OpenSpec intent, first exact gap, and recovery action once for each
operation. Status, plan, prewrite, and hook surfaces SHALL consume that typed
resolution without reclassifying its authority, gap, or next action.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, and a hook evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

### Requirement: Continuation derives from explicit result facts

The schema-version-`2` result SHALL carry `user_decision_required` as an
explicit typed fact selected by the owning resolution. `continuation` SHALL be a
pure projection from verdict, the presence of the sole next action, and that
fact. ETHOS SHALL NOT infer an authority boundary by parsing command text,
English phrases, or gap-name suffixes.

#### Scenario: A mutating-looking command is already authorized

- **WHEN** a result exposes an executable next action and explicitly states that no user decision is required
- **THEN** `user_decision_required` remains false
- **AND** Continuation is `continue` for a passing result or `blocked` for a non-passing result

#### Scenario: Human authority is required

- **WHEN** the owning resolution explicitly marks that handoff, authorization, or confirmation is required
- **THEN** `user_decision_required` is true
- **AND** Continuation is `await-user` without inspecting the action string or gap spelling

### Requirement: Result projection preserves diagnostic execution facts

When a command cannot resolve or execute a required tool or projection, the
owning resolution SHALL preserve the exact boundary facts needed to recover,
including the attempted binary or route, cwd, captured stderr, and relevant
environment projection. A projection failure SHALL NOT be relabeled as adoption
failure or product-test failure.

#### Scenario: Official projection is unavailable from the working tree

- **WHEN** official OpenSpec artifacts exist but the selected projection cannot be read
- **THEN** the result identifies the exact OpenSpec command, cwd, exit status, and stderr
- **AND** the sole next action repairs or completes that projection rather than running `ethos adopt`

#### Scenario: A continuation route is unsupported

- **WHEN** a continuation token is sent to the wrong execution route or a capability is unavailable
- **THEN** the structured result distinguishes wrong route, unavailable capability, and provider finalization failure
- **AND** it states whether mutation occurred and names the sole safe continuation without replaying the mutation

### Requirement: Git signature trust observations are line-ending portable

ETHOS SHALL recognize an otherwise valid Git SSH signature status independent
of whether the host emits LF or CRLF line endings, while malformed or
unsuccessful verification remains untrusted.

#### Scenario: Windows emits a valid CRLF signature status

- **WHEN** Git successfully verifies an object and emits the trusted SSH status
  with CRLF line endings
- **THEN** ETHOS records the same principal and fingerprint as for LF output
- **AND** no signature trust gap is reported.

#### Scenario: Verification output is not a valid terminal status

- **WHEN** Git fails verification or the successful output does not contain the
  complete trusted SSH status
- **THEN** ETHOS reports the corresponding typed signature gap
- **AND** does not infer trust from a partial or malformed line.

### Requirement: Package smoke preserves publication failure facts

The installed-package smoke owner SHALL expose the exact publication required
gaps when the expected full-ref transition plan is unavailable.

#### Scenario: Publication planning is blocked

- **WHEN** the installed CLI returns no full-ref compare-and-swap effect or
  reports a publication topology or source gap
- **THEN** package smoke fails with the exact required gaps and command context
- **AND** does not replace them with only a generic unavailable-plan message.
