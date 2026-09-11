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
  the Change and independently observed expected Git HEAD
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
invocation holder reference matching its exact lane ref, holder ref, positive
generation, and expiry. The mutation request SHALL bind the fresh Work Lane HEAD
as an independent Git fact rather than persisting it in the Lease.

#### Scenario: invocation binding is stale or foreign

- **WHEN** `ethos lane prewrite` runs with a different lane ref, holder ref,
  generation, or expiry than the current Lease, or with a stale independently
  observed Git HEAD
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
compiles the optional tracked `[commit_policy]` declaration from
`.ethos/workspace.toml`, validates the explicit commit subject, projects any
required signing configuration into Git execution, and verifies the resulting
object before a ref, Lease, or worktree effect.

#### Scenario: Signing is enabled and trusted

- **GIVEN** the tracked commit policy requires signing
- **WHEN** a lifecycle operation creates a commit object
- **THEN** the Git invocation requires the declared signing format even when
  ambient or local `commit.gpgsign` is absent or false
- **AND** external trust verification passes before any repository effect.

#### Scenario: Signing is disabled

- **WHEN** a repository has no `[commit_policy]` declaration or its tracked
  policy does not require signing
- **THEN** ETHOS adds no repository-independent subject or signing constraint
- **AND** mutable Git configuration does not become an implicit ETHOS policy.

#### Scenario: Tracked commit policy is malformed

- **WHEN** a present commit-policy table has an unknown field, invalid type,
  invalid subject expression, or unsupported signing format
- **THEN** the lifecycle operation reports the exact policy gap before invoking
  a mutating Git command
- **AND** it does not fall back to ambient Git policy.

#### Scenario: Generated subject is not admitted

- **WHEN** an ETHOS lifecycle operation proposes or receives a subject that does
  not match the tracked `subject_pattern`
- **THEN** the operation blocks before object creation and exposes one explicit
  subject input as its continuation
- **AND** ETHOS does not emit a hard-coded universal replacement subject.

#### Scenario: Required signature is not trusted

- **WHEN** object creation, signing, or external trust verification fails under
  a tracked signing requirement
- **THEN** the lifecycle operation reports the typed signing gap with the Git
  execution diagnostics
- **AND** no ref, Lease, or worktree effect remains.

### Requirement: Publish is the sole remote Git object projection command

`ethos publish` SHALL alone compile, persist and apply remote Git object effects.
It SHALL select typed targets from positive repository topology; bind exact local
objects and proof Attestations; persist one content-addressed request; recheck
all targets before effects; apply peer-local exact CAS; and attest partial or
complete results in machine-readable form. Tags and protected branches SHALL be
modes of this command, not separate commands or hook exceptions.

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

ETHOS SHALL resolve role, actor, Lease, fresh Git facts, official intent, first
gap and recovery once per operation. Status/plan/prewrite/hooks/prove/archive
SHALL consume that typed authority, gap, next action and Commitment unchanged.
Non-pass SHALL stop downstream work; pass alone authorizes plan compilation.
Effects MAY recheck exact CAS or issuance preconditions, SHALL observe results,
and SHALL NOT reselect intent.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, a hook, and prove evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A failed current resolution closes downstream planning

- **GIVEN** the shared current resolver returns a non-passing verdict, ordered gaps, one recovery action, and a user-decision fact
- **WHEN** a public operation consumes that resolution
- **THEN** it projects those fields unchanged and terminates before invoking its operation-specific planner, gate runner, or effect
- **AND** a command-local exception mapper cannot replace the failed resolution

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

#### Scenario: Archive planning reuses the selected intent

- **GIVEN** one archive invocation resolves a completed official Change and its Commitment
- **WHEN** archive readiness and the exact Git-effect plan are compiled
- **THEN** both consume that same current resolution
- **AND** neither rereads OpenSpec governance nor reloads Commitment

#### Scenario: Interrupted archive finalization preserves source identity

- **GIVEN** the worktree contains an exact staged official archive post-image while HEAD still contains the active Change
- **WHEN** the archive operation is resumed
- **THEN** the current resolver compiles intent once from that exact source HEAD
- **AND** the effect plan binds the same Commitment before applying exact CAS

#### Scenario: Archive post-observation does not reselect intent

- **WHEN** the admitted archive Git effect completes
- **THEN** ETHOS re-observes the resulting OpenSpec lifecycle to verify the postcondition
- **AND** that post-observation cannot replace the Commitment already bound into the plan

#### Scenario: Passing resolution freezes plan compilation

- **GIVEN** the shared current resolver returns a passing result
- **WHEN** an operation compiles its deterministic TransitionPlan
- **THEN** the planner consumes the authority, Lease generation, Commitment, scope, and Git facts from that resolution
- **AND** the planner does not reread those mutable inputs or perform a second authority decision

#### Scenario: Repository proof without active intent remains explicit

- **GIVEN** a candidate or accepted root has no active Change and no applicable archive Attestation
- **WHEN** ETHOS resolves current proof input without an explicit Change request
- **THEN** the shared resolver returns a passing repository resolution with no Commitment
- **AND** proof planning consumes that explicit result rather than ignoring an intent-resolution failure

#### Scenario: Attestation issuance rechecks mutable preconditions

- **GIVEN** a plan compiled from one passing frozen resolution
- **WHEN** ETHOS is about to issue the proof Attestation
- **THEN** the issuance owner re-observes exact HEAD, tree, repository identity, Lease generation, and invocation actor
- **AND** it rejects drift without recompiling the plan or selecting different intent

#### Scenario: Work Lane migration uses current policy

- **GIVEN** a Work Lane was created under a historical governance declaration
- **WHEN** ETHOS refreshes it onto an exact current candidate commit
- **THEN** commit grammar and signing policy are compiled from that candidate commit
- **AND** historical policy fields cannot block or authorize the migration
- **AND** branch-role observation ignores retired transition material that it does not own
- **AND** strict ref-mutation admission still requires the exact current branch-role schema

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

### Requirement: Git trust anchors use native host protection

ETHOS SHALL admit external Git trust anchors only when native host authorization
protects the anchor and parent from untrusted modification. Created anchors
SHALL meet the same contract. Failed establishment SHALL retain the bounded host
process reason. Windows PowerShell children SHALL resolve native security
modules independently of incompatible module paths inherited from another
PowerShell edition.

#### Scenario: POSIX anchor is owner-protected

- **WHEN** a trust anchor and its parent are not writable by group or other
  identities under the POSIX permission model
- **THEN** ETHOS admits the protection fact
- **AND** preserves the existing signature verification behavior.

#### Scenario: Windows anchor is ACL-protected

- **WHEN** a Windows trust anchor is owned by the current identity and its file
  and parent DACLs grant write-like authority only to the current identity or
  operating-system administrative identities
- **THEN** ETHOS admits the protection fact independent of emulated POSIX mode
  bits.

#### Scenario: Windows parent shell exports an incompatible module path

- **WHEN** ETHOS launches Windows PowerShell from a parent process whose
  `PSModulePath` belongs to another PowerShell edition
- **THEN** the child reconstructs its native module path and loads the security
  commands required to establish and observe the DACL
- **AND** unrelated inherited environment values remain available.

#### Scenario: Windows anchor is foreign-writable

- **WHEN** the anchor or its parent grants write-like authority to another
  principal, or native ACL facts cannot be obtained
- **THEN** ETHOS reports `git_object_trust_anchor_unprotected`
- **AND** does not infer protection from `chmod`, platform name, or successful
  signature verification alone.

#### Scenario: Windows protection operation fails

- **WHEN** the native Windows operation cannot establish the required DACL
- **THEN** ETHOS fails closed with `git_object_trust_anchor_protection_failed`
- **AND** preserves the child exit code and bounded native error text.

### Requirement: Empty changed scope closes without historical intent

When fresh Git observation reports no changed paths, `ethos plan --changed`
SHALL return a successful no-op result without selecting active or archived
OpenSpec intent, compiling proof gates, or applying historical archive scope to
the empty observation.

#### Scenario: Clean repository has no changed-scope work

- **WHEN** `ethos plan --changed --json` runs in a clean governed repository
- **AND** fresh Git observation reports zero changed paths
- **THEN** the result passes with `changed=false` and zero plan nodes
- **AND** the result contains no `proof_archive_scope_stale` gap
- **AND** no active or archived Change is selected as current intent.

#### Scenario: Non-empty changed scope remains governed

- **WHEN** `ethos plan --changed --json` observes one or more changed paths
- **THEN** the current official Change and archive authority rules remain in
  force
- **AND** stale or insufficient archive scope still fails closed.

### Requirement: Lane retirement exposes one receipt-bound recovery route

The `ethos lane retire` command family SHALL expose one public `recover`
operation for every partial linked-lane retirement. The operation MUST accept
an immutable receipt path and digest, return the currently observed effect
progress as structured JSON, and provide exactly one copyable continuation.
It SHALL never require raw Git, direct SQLite mutation, or recreation of a
deleted checkout.

#### Scenario: Partial retirement returns its continuation

- **WHEN** a retirement effect completes but the terminal worktree, ref, and
  Lease postcondition is not reached
- **THEN** the command returns a blocking structured result with
  `state=partial_transition`, the immutable receipt identity,
  `completed_effects`, and `remaining_effects`
- **AND** `next_action` is the complete `ethos lane retire recover` command for
  that receipt.

#### Scenario: Recovery is dry-run before apply

- **WHEN** `ethos lane retire recover` is invoked without `--apply`
- **THEN** it performs only receipt validation and fresh observation
- **AND** it reports the exact remaining effects and the authorized apply
  command without changing Git, worktree, or Lease state.

#### Scenario: Recovery execution is structured and idempotent

- **WHEN** recovery is authorized and applied one or more times
- **THEN** every invocation returns structured JSON without a traceback
- **AND** terminal state is either newly applied or recognized from the same
  immutable request.

### Requirement: Commit policy has one executable admission surface

ETHOS SHALL expose one JSON-composable commit-range admission command under the
existing hook command namespace. The command SHALL accept explicit named target,
proposed-head, remote-head, remote, and optional trusted-baseline coordinates and
SHALL return the exact range, policy projection, checked commit count, violations,
stable gaps, and one next action without performing a mutation.

#### Scenario: A local or hosted transport requests range admission

- **WHEN** `ethos hook commit-range` receives complete readable coordinates
- **THEN** it invokes the same repository range and commit-policy owner used by
  pre-push
- **AND** its JSON verdict is independent of GitHub, GitLab, or shell syntax.

#### Scenario: Coordinates are stale or incomplete

- **WHEN** an endpoint, baseline, committed policy, or introduced range cannot
  be read exactly
- **THEN** the command fails closed with the failing coordinate and stable gap
- **AND** it does not infer a replacement revision or inspect all history.

### Requirement: Git commit-message admission validates the final subject

The package runtime SHALL execute a `commit-msg` hook that reads the final
message file and compiles commit policy from the prospective index tree. It SHALL
validate only the first message line before Git creates the commit and SHALL NOT
claim that a not-yet-created object has a valid signature.

#### Scenario: Raw Git commit has an invalid subject

- **WHEN** a repository with a valid commit policy invokes ordinary `git commit`
  with a non-conforming final subject
- **THEN** the installed `commit-msg` transport rejects object creation with
  `commit_subject_invalid`
- **AND** it uses no parser or grammar other than the existing `CommitPolicy`.

#### Scenario: The staged policy changes in the same commit

- **WHEN** `.ethos/workspace.toml` is added, changed, or removed in the index
- **THEN** `commit-msg` evaluates the exact policy represented by that index
- **AND** unstaged working-tree bytes do not govern the prospective commit.

#### Scenario: Local commit-message transport is bypassed

- **WHEN** a commit is created with `git commit --no-verify`
- **THEN** no local pre-object claim is made
- **AND** pre-push and hosted commit-range admission still validate the created
  object through the same policy owner.

### Requirement: Commit-policy enforcement capability is discoverable

Repository status SHALL report whether the optional policy is declared and
whether the installed `commit-msg` and `pre-push` transports are exact current
launchers for the selected immutable runtime.

#### Scenario: Required transport is missing or stale

- **WHEN** a declared policy exists but either launcher is absent, modified, or
  bound to a stale runtime generation
- **THEN** status identifies the unavailable enforcement boundary
- **AND** it returns the existing exact `ethos hook install --root <root> --json`
  repair command rather than asking the adopter to inspect source.

#### Scenario: A new transport exists only in an unaccepted Change

- **WHEN** the selected immutable runtime exactly matches accepted Git truth but
  the invoking Work Lane contains a newer commit-policy execution capability
- **THEN** status keeps the accepted runtime current and reports the newer
  capability as `pending_acceptance`
- **AND** it does not instruct the older accepted runtime to install a launcher
  or command that package does not contain.

#### Scenario: Accepted source requires a newer runtime

- **WHEN** accepted Git truth advances to source whose commit-policy execution
  capability is newer than the selected immutable runtime
- **THEN** status reports the selected runtime stale
- **AND** its repair action invokes the new accepted package rather than asking
  the superseded runtime to manufacture unknown semantics.

#### Scenario: Policy is not declared

- **WHEN** the repository has no `[commit_policy]` declaration
- **THEN** status reports the capability as not declared without adding a gap
- **AND** hook installation remains valid for the repository's other controls.

### Requirement: Reader Observation Completion

ETHOS readers SHALL select continuation from actual pending operations and
unobserved facts. A complete passing observation with neither SHALL have an
empty next action and continuation done. Reader completion SHALL NOT assert
completion of the repository, external delivery or unrelated work.

#### Scenario: Passive accepted checkout has no pending operation

- **WHEN** accepted and candidate coordinates agree and no blocking gap or
  unobserved coordination detail remains
- **THEN** status and lane status return an empty next action and continuation done
- **AND** they do not require a new Change or store observation progress

#### Scenario: Coordination detail is expanded once

- **WHEN** compact status has foreign or unbound lanes requiring detail
- **THEN** it may select the existing lane-status reader
- **AND** complete lane status preserves the coordination facts without selecting itself
- **AND** observation does not authorize writing or retiring foreign content

#### Scenario: Accepted candidate still needs closeout

- **WHEN** a candidate is a distinct admissible successor of accepted HEAD
- **THEN** both readers reuse the same exact closeout derivation
- **AND** they do not replace that operation with done or a re-observation loop

#### Scenario: A necessary input is blocked or unavailable

- **WHEN** current authority, topology or scope cannot admit progress
- **THEN** the existing blocking or unknown verdict and its cause are preserved
- **AND** the absence of a next action does not turn that result into done

### Requirement: Source-complete intent context

ETHOS SHALL preserve every unique official context document's repository path,
exact content and content digest in its transient planning projection. It SHALL
report missing, unreadable, invalid or escaping sources instead of silently
omitting them. Native Markdown syntax SHALL determine auxiliary section views.

#### Scenario: Equivalent official Markdown preserves constraints

- **WHEN** non-goals or open questions use bullet, ordered, wrapped or paragraph forms
- **THEN** the context retains their complete text and exact source content
- **AND** fenced headings do not create real sections and peer headings end sections

#### Scenario: An observed source cannot be consumed

- **WHEN** the official context names an unavailable, invalid or escaping source
- **THEN** the result identifies that source gap and does not claim complete context
- **AND** source observation does not authorize reading outside the repository

#### Scenario: Duplicate paths do not create duplicate evidence

- **WHEN** multiple official artifact roles refer to the same document
- **THEN** the document is read once and represented once in deterministic path order
- **AND** its repeated reference does not imply independent supporting evidence

### Requirement: Structural compilation does not certify interpretation

ETHOS SHALL distinguish source preservation and structural compilation from
acceptance of an interpretation, sufficient verification, admitted effects and
achieved user outcomes. The repository handoff procedure SHALL require relevant
source constraints to be retained, explicitly excluded by an authorized decision
or marked unresolved before claiming intent alignment.

#### Scenario: The zero-winner requirement is mistranslated

- **WHEN** the source permits all candidates to be dropped with useful results preserved
- **AND** a candidate interpretation requires exactly one winner
- **THEN** both original constraint and candidate interpretation remain available for review
- **AND** successful parsing or compilation does not certify that interpretation
- **AND** an Agent following the handoff procedure rejects the added winner obligation

#### Scenario: Cooperation and dropping do not imply destruction

- **WHEN** compatible contributions are combined or no competing candidate is selected
- **THEN** the accepted intent may select multiple cooperative contributions or zero competing winners
- **AND** dropping integration does not authorize loss of useful conclusions or unique results

### Requirement: Accepted signature repair command

ETHOS SHALL expose a public, bounded repair for one exact unsigned accepted
commit. Readiness SHALL have no Git-object, ref or worktree mutation. Explicitly
authorized application SHALL create a trusted replacement, apply selected local
effects, and report completed, blocked, unknown or recoverable outcomes.

#### Scenario: Readiness has no signing effect

- **WHEN** an operator requests signature-repair readiness for an exact accepted head
- **THEN** ETHOS reports current prerequisites and the authorized apply action
- **AND** it does not create a replacement object or move refs or worktrees

#### Scenario: Application requires authorization

- **WHEN** repair application lacks explicit authorization or has stale coordinates
- **THEN** it rejects the request before creating a replacement object
- **AND** it identifies the failed boundary and one fresh next action

#### Scenario: Successful repair requires new proof

- **WHEN** the selected local repair effects finish and their postconditions hold
- **THEN** the result identifies the replacement commit and exact reproof command
- **AND** it does not claim proof, runtime activation or remote publication

#### Scenario: Recovery observes instead of repeating effects

- **WHEN** a signing or ref effect has completed but its acknowledgement was lost
- **THEN** recovery uses durable result evidence and current Git observations
- **AND** it does not create another replacement or repeat completed effects
- **AND** missing evidence remains unknown rather than implying completion
