## ADDED Requirements

### Requirement: Worktree Family
One ChangeContract MUST derive one Worktree Family with zero or more cooperative
slots, at most two competitive variants, read-only research workers, and exactly
one canonical family head eligible for candidate integration. Its Lease MUST
persist only the immutable base ChangeContract digest as lineage identity. The
admitted amendment set is empty in this release, so the selected and effective
ChangeContract are the base ChangeContract.

#### Scenario: Two alternative implementations compete
- **WHEN** both variants satisfy the same acceptance contract
- **THEN** a selection attestation chooses one canonical head, records absorbed intent, and leaves the losing variant in a retireable state

#### Scenario: A future amendment resolver is introduced
- **WHEN** a later release admits intent amendments
- **THEN** only Git-reachable, authority-admitted, digest-chained amendment
  Attestations may be folded by the resolver
- **AND** the Lease retains the same base ChangeContract digest and wire
- **AND** no Lease migration, alias, fallback, or parallel binding store is
  created

### Requirement: ChangeContract And Attestation Admission
Current repository-semantic admission SHALL use the selected ChangeContract,
fresh RepositoryFacts, transient PlanIR, and verifier-bounded Attestations. It
SHALL create no separate proposition envelope, evidence-freshness store,
semantic-receipt entity, or persisted parallel lifecycle owner.

#### Scenario: Evidence-bearing proposition is evaluated
- **WHEN** a selected ChangeContract requires a verifier-bounded proposition
- **THEN** the applicable Attestation binds evidence references, selected
  ChangeContract digest, exact subject and HEAD, verifier scope, verdict, and
  validity boundary
- **AND** missing, malformed, stale, or mismatched evidence fails closed

#### Scenario: Semantic assurance is required
- **WHEN** the selected ChangeContract requires semantic assurance
- **THEN** one candidate-external Attestation binds the semantic scope and exact
  HEAD with a non-authorizing verdict
- **AND** digest-only propositions remain portable without a provider

#### Scenario: Current lifecycle state is persisted
- **WHEN** ETHOS persists repository-semantic state
- **THEN** ChangeContract and Attestation are the only persistent semantic entities
- **AND** behavior scope remains exact to the selected contract and verifier
  boundary

### Requirement: Adaptive Backpressure
Concurrency admission MUST derive from conflict density, host capacity, proof latency, queue age, candidate throughput, and recoverability rather than a fixed global WIP limit.

#### Scenario: Independent low-conflict changes are ready
- **WHEN** host and proof capacity are available and their declared scopes do not overlap
- **THEN** the scheduler may admit them concurrently even when three other changes exist

### Requirement: Candidate Compare-and-swap Train
Authoring and proof MAY run concurrently, but candidate advancement MUST be a short serialized compare-and-swap against the observed candidate head.

Candidate, accepted, and release roots MUST remain free of active OpenSpec Change
carriers. New authoring lanes MUST receive intent only from one explicit source
Work Lane and MUST bind the materialized carrier before a Lease becomes active.

#### Scenario: Candidate advances during proof
- **WHEN** a proven family attempts to land against a stale candidate head
- **THEN** the update is rejected and the family refreshes and re-proves rather than overwriting candidate state

#### Scenario: New lane continues an existing intent
- **WHEN** a clean protected root starts a destination lane from an explicit
  source Work Lane
- **THEN** candidate contributes only the clean integration base
- **AND** the source contributes only the selected active Change carrier
- **AND** the destination initialization commit and Lease are the first combined
  authoritative state

### Requirement: Provider-neutral Proposal Role
The self profile MUST publish only `main`, `dev`, and `proposal/*`; `candidate/dev` and `work/*` MUST remain local-only.

#### Scenario: A local authoring branch is selected for push
- **WHEN** its role is candidate or work
- **THEN** publication blocks before any remote mutation

### Requirement: Active OpenSpec Coverage Is Contract-owned
An adopter's material-path classification MUST be matched only against the
selected active ChangeContracts. There MUST be no bootstrap, repair, verifier-bounded proposition
binding, or archive-carrier exception in the active verdict.

#### Scenario: A retired scope file exists
- **WHEN** the active ChangeContract covers the material path
- **THEN** the contract decides coverage and the legacy file cannot widen it

#### Scenario: A complete Change remains in the active directory
- **WHEN** a new material write matches its historical scope
- **THEN** the complete Change is visible to lifecycle review but cannot authorize the write

### Requirement: Non-locking Git Observation
Read-only lifecycle observation MUST use one isolated Git execution profile with
optional locks disabled. Git effects and handoff import/export MUST retain their
normal mutation environment.

#### Scenario: A lane is observed during concurrent work
- **WHEN** ETHOS reads refs, worktree status, tracked differences, or untracked paths
- **THEN** every Git observation uses `GIT_OPTIONAL_LOCKS=0`, fixed locale, and
  isolated Git configuration
- **AND** no inherited repository override can redirect the observation

#### Scenario: A Git effect executes
- **WHEN** ETHOS updates a ref, worktree, hook, bundle, or configuration
- **THEN** the observation profile is not applied implicitly

### Requirement: Authorized Lease Takeover
A foreign Work Lane lease MAY change holder without a source-holder handoff only
through one explicitly authorized takeover bound to the exact branch, HEAD,
lease generation, current dirty-content digest, destination actor, and declared
source-session state. The effect MUST use one local compare-and-swap, increment
the lease epoch, preserve `mints_authority = false`, and emit the authorization
reference and source-state boundary in its effect Attestation.

#### Scenario: The source controller is quiescent
- **WHEN** the destination actor supplies the exact lease tuple and dirty digest,
  an authorization reference, a reason, and `source_state = "quiesced"`
- **THEN** takeover atomically replaces the holder and increments the epoch

#### Scenario: The source session is lost
- **WHEN** current authority explicitly authorizes takeover with
  `source_state = "lost"`
- **THEN** the effect Attestation preserves that the source quiescence was not directly
  observed rather than claiming a normal handoff

#### Scenario: Target state drifts before takeover
- **WHEN** the branch, HEAD, lease tuple, actor, or dirty-content digest differs
  from the authorized request
- **THEN** takeover blocks without changing the lease

### Requirement: Absorptive Knowledge Retirement
Current semantic carriers SHALL retire only after independent meaning and
scenarios are assigned to one authoritative destination and verified. Historical
carriers remain immutable but non-normative.

#### Scenario: Two valid meanings do not fit the current model
- **WHEN** retirement would lose either meaning
- **THEN** retirement blocks and preserves both carriers
- **AND** it invokes [Model Promotion](../../../../../docs/governance/product-design-contract.md#model-promotion)
  requirement before either carrier is retired

#### Scenario: Meaning has one verified owner
- **WHEN** every current rule, rationale, and scenario is absorbed and re-verified
- **THEN** the redundant carrier is removed rather than retained as an alias,
  fallback, shim, compatibility path, or parallel truth

### Requirement: Active ChangeContract Carrier Closure

ETHOS SHALL derive active-carrier closure from each selected ChangeContract,
fresh carrier observations, and required Attestations. Archive location is an
observation, not lifecycle authority or a separate program state.

#### Scenario: archived carrier is presented as active

- **WHEN** a selected ChangeContract resolves only under the OpenSpec archive
- **THEN** PlanIR rejects treating that carrier as active
- **AND** archive location alone does not mint current lifecycle truth

#### Scenario: archived carrier awaits land

- **WHEN** an archived selected ChangeContract lacks required landing
  Attestations
- **THEN** carrier closure remains unfinished
- **AND** the archive remains immutable while current proof is recomputed

#### Scenario: pre-land state still references an active carrier

- **WHEN** a selected ChangeContract declares archived or landed state but
  resolves in the active directory
- **THEN** PlanIR reports a carrier-location mismatch

#### Scenario: terminal step lacks archived carrier

- **WHEN** a selected ChangeContract is reported terminal without an archived
  carrier observation
- **THEN** carrier closure blocks

#### Scenario: campaign awaits a planned successor

- **WHEN** a selected ChangeContract is complete and a successor is only planned
- **THEN** carrier closure for the selected set may complete
- **AND** the successor remains outside the set until explicitly selected
- **AND** no planned entry becomes an active Work Lane

### Requirement: Selected ChangeContract Aggregate Predicate

ETHOS SHALL compile one aggregate PlanIR predicate over an explicit set of
selected base ChangeContract digests, fresh RepositoryFacts, and required
Attestations. Selection creates no manifest, store, command root, or lifecycle
owner.

#### Scenario: Campaign status reports lane steps

- **WHEN** status or plan reads an exact selected ChangeContract set
- **THEN** the result reports contract digests, Work Lane facts, dependencies,
  and verdicts
- **AND** ordered PlanIR nodes replace campaign step state

#### Scenario: Campaign closeout includes campaign package

- **WHEN** prove, land, or publish evaluates the selected set
- **THEN** the aggregate predicate combines required observation, judgment,
  proof, and effect Attestations
- **AND** unselected future ChangeContracts do not block the selected set

#### Scenario: Campaign closeout scopes one explicit campaign

- **WHEN** planning receives exact selected base ChangeContract digests
- **THEN** only those ChangeContracts contribute PlanIR nodes and gaps
- **AND** the requested selector is recorded in the plan
- **AND** unrelated ChangeContracts remain outside the selected predicate

### Requirement: Selected ChangeContract Protected-Publication Admission

Protected publication SHALL evaluate the selected ChangeContract aggregate,
active-carrier closure, direct source measurement, exact local protected HEAD,
and required Attestations before remote mutation. It creates no program state.

#### Scenario: A campaign remains unfinished

- **WHEN** any selected ChangeContract, carrier closure, source measurement, or
  required Attestation is blocked, unknown, or stale
- **THEN** status, proof, land, hooks, and publish expose the blocking predicate
- **AND** protected mutation stops before remote effects

#### Scenario: The campaign terminal is ready

- **WHEN** every selected ChangeContract has carrier closure, a terminal verdict,
  and current required Attestations
- **THEN** protected-publication admission adds no aggregate-completion gap
- **AND** identity, candidate topology, and provider checks remain independent
- **AND** publication still requires the exact local protected HEAD

#### Scenario: Invalid Campaign declaration fails closed

- **WHEN** the selected ChangeContract set is malformed, ambiguous, or
  references an unknown selected base digest
- **THEN** strict planning rejects the selection
- **AND** protected publication remains blocked

#### Scenario: Campaign action commands remain external

- **WHEN** admission selects local continuation or protected publication
- **THEN** it returns an action identifier rather than embedded command text
- **AND** Cyclopts declarations remain the command source

#### Scenario: Filtered Campaign status preserves repository scope

- **WHEN** status filters an exact selected ChangeContract set
- **THEN** the selected views are returned without changing the repository
  subject
- **AND** repository-wide blockers remain visible
- **AND** filtering creates no second lifecycle truth

#### Scenario: Hook evaluates the named remote and branch policy

- **WHEN** pre-push evaluates one named remote and receiving branch
- **THEN** the exact remote and branch enter protected-publication admission
- **AND** diagnostics name that provider
- **AND** ordinary Work Lane remote policy remains independently enforced

### Requirement: ChangeContract Hypotheses And Attested Learning

Hypotheses and experiments SHALL live in ChangeContract.hypotheses. Their observations, judgments, proof, and effects are Attestations; no separate learning persistence owner exists.

#### Scenario: Hypotheses are inspected

- **WHEN** plan reads ChangeContract.hypotheses
- **THEN** each hypothesis exposes its question, falsifier, and current Attestation references

#### Scenario: Evolution declarations compile without a runtime owner

- **WHEN** a ChangeContract proposes research, hypothesis, or experiment work
- **THEN** PlanIR orders checks over fresh RepositoryFacts and prior Attestations
- **AND** observations, judgments, and proof remain typed Attestations
- **AND** no ledger, runtime owner, or hidden state becomes authority

#### Scenario: evolution commands and gates use one ledger

- **WHEN** status, plan, proof, or projections inspect learning state
- **THEN** they read ChangeContract.hypotheses and referenced Attestations
- **AND** documentation carries no parallel ledger
- **AND** observation Attestations bind evidence references
- **AND** judgment Attestations bind the selected outcome
- **AND** proof Attestations bind the verifier and validity boundary

#### Scenario: practice is judged before carrier adoption

- **WHEN** a framework, workflow, skill, or tool proposal is evaluated
- **THEN** the ChangeContract states the hypothesis and commitment effect
- **AND** Attestations record confirming or falsifying observations
- **AND** the carrier remains subordinate to the accepted judgment

#### Scenario: practice proposition carries commitment effect

- **WHEN** a reusable practice proposal enters a ChangeContract
- **THEN** its hypotheses name the question, candidates, falsifiers, and intended commitment effect
- **AND** observation and judgment Attestations record evaluation
- **AND** candidate tools and workflows remain replaceable carriers

#### Scenario: candidate set is evaluated

- **WHEN** multiple candidates answer the same governed question
- **THEN** the ChangeContract identifies each candidate and common acceptance boundary
- **AND** proof Attestations record comparable results
- **AND** a judgment Attestation records the selected and rejected candidates

#### Scenario: practice fate is classified

- **WHEN** the selected judgment admits, composes, refines, supersedes, retires, or rejects a practice
- **THEN** the judgment Attestation records that fate and its evidence basis
- **AND** any realized repository change remains a separately verified effect Attestation

#### Scenario: ledger records candidate selection objects

- **WHEN** a candidate selection is compiled
- **THEN** the ChangeContract carries hypotheses, candidates, experiment protocol, and acceptance
- **AND** every observation, proof, and judgment reference resolves to an Attestation

### Requirement: Bounded Comparative Assurance Gate

Comparative assurance SHALL run only as a prove gate. It emits a bounded Attestation and creates no command family, schema, root, tracked evidence plane, or lifecycle owner.

#### Scenario: Bounded Attestation binds proof inputs

- **WHEN** prove evaluates an explicit target
- **THEN** the resulting Attestation binds target HEAD, product HEAD, compared checks, and input digests
- **AND** the verifier and validity boundary are explicit
- **AND** no tracked evidence file or schema is created

#### Scenario: Attestation records missing blocking gap

- **WHEN** a reference result omits a required blocking gap
- **THEN** the prove gate returns block
- **AND** the Attestation records the missing gap without asserting transition completion

#### Scenario: Changed proof input makes Attestation stale

- **WHEN** a Work Lane changes a proof input
- **THEN** prove marks the prior Attestation stale
- **AND** the gate must be rerun in the Work Lane
- **AND** candidate and accepted roots remain write-protected
- **AND** stale evidence cannot become a green verdict

#### Scenario: Current Attestation is required before proof and land

- **WHEN** a Work Lane reruns proof after its source change
- **THEN** proof consumes the new bounded Attestation
- **AND** landing waits for that proof
- **AND** no separate evidence commit or tracked evidence plane is required

#### Scenario: Attestation establishes generic coverage

- **WHEN** an explicit target has a current bounded Attestation
- **THEN** prove reports no covered capability gap
- **AND** the Attestation covers OpenSpec, lifecycle, proof, and profile boundaries
- **AND** product packages remain free of adopter-private terminology

#### Scenario: Checkout-bound execution substrate outranks stale environment

- **WHEN** the gate finds a checkout-bound runtime and a stale unrelated environment
- **THEN** it executes with the checkout-bound execution substrate
- **AND** the bounded Attestation reports the current result rather than a stale-environment failure

### Requirement: Attested Execution Substrate Transition

Execution-substrate conformance SHALL remain generic and replaceable. It SHALL
require or prefer no runtime or backend; admission remains demand-driven under
terminal-convergence task 3.7.

#### Scenario: Execution substrate transition is judged

- **WHEN** a selected ChangeContract judges a replaceable execution-substrate
  transition for a repository
- **THEN** present configuration and Git state are freshly observed
  RepositoryFacts
- **AND** equivalence or stricter comparative evidence is a `proof` Attestation
  with an explicit false-negative boundary
- **AND** switch, removal, and rollback are exact-HEAD/tree `effect`
  Attestations bound to a reachable Git recovery anchor
- **AND** retirement authorization is a `judgment` Attestation
- **AND** history is derived and no retirement entity, store, manifest type,
  schema, command family, ledger, or profile state is created

### Requirement: Exact Work Lane Lifecycle Effects

ETHOS SHALL keep routine lease coordination and its postcondition receipts in
ignored local state. Linked Work Lane retirement SHALL expose only the exact
holder-bound `landed` and `superseded` transitions. Foreign holder changes SHALL
use handoff or exact authorized Lease takeover. Unknown, dirty, unbound, or
owner-uncertain state SHALL remain observe-only and blocked. Chronicle is derived
history and never authorization.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and an ignored local
  postcondition receipt
- **AND** routine coordination produces no effect Attestation or tracked
  lifecycle telemetry

#### Scenario: exceptional state does not widen lifecycle effects

- **WHEN** orphan recovery, foreign retirement, unbound deletion, preservation,
  or another exceptional cleanup is requested
- **THEN** this release exposes no generic cleanup or Resolution transition
- **AND** the target remains observe-only and blocked unless normal holder-bound
  handoff, takeover, `landed`, or `superseded` admission applies
- **AND** a future generic recovery effect requires its own selected
  ChangeContract rather than a hidden compatibility path

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, lease, contents, or recovery state is dirty, missing,
  ambiguous, or unknown
- **THEN** ETHOS preserves and blocks the lane
- **AND** current lifecycle output does not offer retirement, cleanup, or raw Git
  deletion as a next action

#### Scenario: break-glass remains outside normal lifecycle

- **WHEN** a predeclared selected ChangeContract and accepted judgment
  Attestation bind the exact emergency target, policy, blast radius, and expiry
- **THEN** normal Work Lane lifecycle commands do not reinterpret that judgment
  as holder, retirement, or cleanup authority
- **AND** any emergency effect and later reconciliation remain separately
  admitted ChangeContracts outside the normal lane lifecycle
- **AND** a self-supplied flag, holder string, or historical projection grants no
  authority

#### Scenario: exceptional handoff is attested

- **WHEN** an exceptional handoff becomes disputed
- **THEN** the selected ChangeContract and accepted judgment Attestation bind
  the exact lane and policy
- **AND** Chronicle derives the historical view only after that Attestation and
  does not authorize the handoff
- **AND** the judgment does not replace the destination Lane Lease

#### Scenario: unknown holder facts remain blocked observations

- **WHEN** holder evidence is missing, stale, ambiguous, or obsolete
- **THEN** RepositoryFacts remain blocked observations
- **AND** a derived historical projection may provide context but does not
  authorize retire, preserve, block, handoff, or break-glass
- **AND** dirty or owner-unknown lanes remain preserved or blocked

#### Scenario: linked retirement remains exact and holder-bound

- **WHEN** the current holder requests linked `landed` or `superseded`
  retirement for an exact source branch and HEAD
- **THEN** ETHOS re-observes the source and applies only that exact linked
  lifecycle effect
- **AND** ignored local postcondition evidence records the verified result
- **AND** tree inequality, a missing lease, or a derived historical projection
  grants no authority
- **AND** authority does not extend to another lane or remote mutation

### Requirement: Exact Tracked Mutation Admission

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
- **AND** it resolves the named Work Lane ref as `binding_head` for comparison
  with the lease's `expected_head`
- **AND** ordinary writes bind the lease to current `HEAD`
- **AND** missing named refs, mismatched lease heads, accepted, candidate,
  proposal, other, and unknown detached branches remain protected and fail closed

#### Scenario: refresh-base marks comparative-assurance Attestation stale after projection conflict

- **WHEN** a clean Work Lane replay conflicts only with stale comparative-assurance output
- **THEN** refresh-base completes the Git replay and marks comparative assurance stale
- **AND** the payload requires rerunning prove --gate comparative-assurance
- **AND** no comparison artifact is selected as repository truth
- **AND** the lane is not ready to land until fresh proof passes
#### Scenario: refresh-base keeps semantic conflicts blocked

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts on any path
  outside the admitted projection set
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

## MODIFIED Requirements

### Requirement: Semantic OpenSpec Capability Layout

Accepted capability IDs SHALL express stable product semantics, not package
names; each capability directory and its `spec.md` are sufficient.

#### Scenario: accepted specs use semantic capability IDs
- **WHEN** repository audit inspects `openspec/specs`
- **THEN** it requires the nine accepted semantic directories and each `spec.md`,
  with no package-shaped identity or parallel metadata

### Requirement: Productized OpenSpec carrier governance

OpenSpec SHALL carry accepted specs and active or archived changes while
ChangeContract and evidence refs retain their distinct duties. Archive closeout
SHALL preserve scenario obligations and canonical unique archive identities.

#### Scenario: Archive closeout is a product gate
- **WHEN** downstream work depends on a closed OpenSpec carrier
- **THEN** official archival fuses accepted obligations forward, requires an
  explicit decision for removal, and does not replace ChangeContract acceptance

#### Scenario: Archive identity is canonical and unique
- **WHEN** archive closeout evaluates historical carriers
- **THEN** each `YYYY-MM-DD-<date-free-logical-id>` resolves exactly once and
  numeric-leading, terminal-date, or duplicate identities block closeout

### Requirement: Productized OpenSpec Substrate

ETHOS SHALL provide an inspectable official OpenSpec workspace. An accepted
capability requires only its directory and `spec.md`.

#### Scenario: OpenSpec substrate is inspectable
- **WHEN** ETHOS scaffolds or audits an OpenSpec workspace
- **THEN** workspace, spec, and change guidance exists; accepted directories
  contain `spec.md`; active changes remain carriers; no parallel metadata is required

#### Scenario: OpenSpec metadata compatibility is checked upstream
- **WHEN** ETHOS performs the always-run OpenSpec shape audit
- **THEN** unsupported active or archived `.openspec.yaml` keys are reported
  before an editor or host projection parses them

### Requirement: OpenSpec customization stays official-compatible

Official OpenSpec validation SHALL precede ETHOS carrier, ChangeContract,
accepted-spec identity, proposal-intent, scope, evidence, and archive checks.

#### Scenario: ETHOS validates capability metadata after official OpenSpec
- **WHEN** ETHOS validates an OpenSpec change or accepted spec
- **THEN** official validation runs first, followed by carrier files,
  ChangeContract, `spec.md` identity, exact `subject`/`reuse`/`change`, scope,
  evidence refs, and archive closeout without altered OpenSpec semantics

#### Scenario: clean ownerless landed residual retires after exact accepted absorption
- **GIVEN** one named Work Lane is clean, unleased, and strictly ancestral to accepted
- **WHEN** lifecycle admission observes the exact source and accepted control state
- **THEN** ETHOS reports the lane without offering a retirement effect
- **AND** holder handoff or exact authorized Lease takeover is required before a
  linked `landed` or `superseded` transition
- **AND** inventory, lease expiry, graph relation, or history alone authorizes nothing


### Requirement: Accepted-root closeout is bound to one audited candidate HEAD

Accepted-root closeout SHALL bind the exact candidate Git HEAD and selected base ChangeContract digest as distinct values, together with required proof and effect Attestations.

#### Scenario: Candidate HEAD changes during or after closeout audit

- **WHEN** the candidate Git HEAD differs from the audited HEAD before mutation or postcondition verification
- **THEN** closeout blocks without treating either HEAD as a ChangeContract digest
- **AND** the result reports both the exact candidate HEAD and selected base ChangeContract digest
- **AND** each binding is independently validated against its own source

### Requirement: Cohort-bound full Work Lane convergence

ETHOS SHALL treat a request to converge multiple Work Lanes as an exact,
observation-bound local program and SHALL NOT interpret a branch prefix or
session instruction as reusable wildcard authority.

#### Scenario: a convergence cohort is frozen before mutation

- **GIVEN** a maintainer requests convergence of multiple existing Work Lanes
- **WHEN** the program begins
- **THEN** a separate owned governance Work Lane records the exact branch, HEAD,
  worktree binding, dirty state, lease/incarnation evidence, selected base ChangeContract digest,
  intended disposition, and target-observation evidence for each lane
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
- **WHEN** the lane is evaluated for convergence
- **THEN** fresh RepositoryFacts bind one exact observation
- **AND** the lane remains observe-only and blocked rather than entering a
  Resolution or exceptional-retirement state machine
- **AND** holder handoff or exact authorized Lease takeover is required before
  any linked lifecycle action
- **AND** dirty or stale state never falls back to raw Git deletion.

#### Scenario: local convergence completion keeps evidence planes separate

- **WHEN** all cohort intent has been integrated or explicitly superseded
- **THEN** strict carrier completion, bounded comparative assurance, HEAD-bound executed proof,
  candidate landing, accepted-root closeout, and lane retirement are verified as
  distinct transitions
- **AND** recovery-package retention remains independent
- **AND** local completion does not claim remote push, hosted execution, or
  distribution publication.

### Requirement: Remote reconciliation continuation preserves historical carrier boundaries

If historical remote-reconciliation content landed but lifecycle work remains,
ETHOS SHALL preserve Git history, the OpenSpec archive, and prior Attestations
without claiming completion. An active continuation SHALL bind the effective
ChangeContract digest and the relevant prior Attestations. If the original host
worktree cannot resume, the continuation SHALL use a distinct owned lane on the
current candidate, retain only freshly observed RepositoryFacts, and rerun
current proof; historical proof or reconstructed paths grant no current
authority.

#### Scenario: remaining lifecycle work continues after historical archival

- **WHEN** a historical reconciliation archive records unfinished local
  closeout, remote observation, or retirement work
- **THEN** an active continuation records the transfer against the effective
  ChangeContract digest and relevant prior Attestations
- **AND** it preserves normal merge and no-force constraints
- **AND** it distinguishes local proof, remote mutation, remote observation, and
  hosted-provider observation

#### Scenario: Historical worktree is absent

- **GIVEN** Git history, an OpenSpec archive, and prior Attestations remain
  readable
- **AND** the original host worktree or its checkout-local temporary state is
  absent
- **WHEN** a successor begins continuity work
- **THEN** it records retained source identities, irrecoverable state, current
  Git and Work Lane anchors, and a no-reconstruction boundary
- **AND** it leaves the historical lane and archive observe-only
- **AND** it binds the selected base ChangeContract digest and prior Attestations to
  the active successor before a new proof, land, closeout, or publication attempt

#### Scenario: Current proof follows retained historical meaning

- **GIVEN** a successor continuity packet has preserved the historical meaning
- **WHEN** the successor reaches a stable committed HEAD
- **THEN** ETHOS compiles current RepositoryFacts with the effective
  ChangeContract digest and prior Attestations
- **AND** it reruns current OpenSpec lifecycle and HEAD-bound proof
- **AND** it distinguishes new Attestations from historical proof, temporary
  runtime state, hosted CI, and remote publication

## REMOVED Requirements

### Requirement: Evidence-backed Claims

**Reason**: A separate proposition envelope duplicates ChangeContract and Attestation admission.

**Migration**: The evidence-audit scenario moves to ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Trust-bearing Claim Admission

**Reason**: A separate trust envelope duplicates the selected ChangeContract and verifier-bounded Attestation.

**Migration**: Both trust-carrier scenarios move to ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Claim evidence freshness is explicit

**Reason**: Freshness is an Attestation validity and exact-binding invariant rather than a separate persisted proposition field.

**Migration**: All freshness scenarios move to ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Semantic claim attestations are typed and candidate-external

**Reason**: Semantic assurance is a typed candidate-external Attestation without a second proposition entity.

**Migration**: Both semantic-assurance scenarios move to ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Canonical Persisted Claim Envelope

**Reason**: A persisted parallel envelope violates the two-entity terminal kernel.

**Migration**: Persisted semantic state is represented only by ChangeContract and Attestation under ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Lifecycle claim semantic scope is behavior-exact

**Reason**: Behavior-exact scope belongs to the selected ChangeContract and verifier-bounded Attestation.

**Migration**: All behavior-scope scenarios move to ChangeContract And Attestation Admission.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

**Reason**: Carrier closure changes when active and archived OpenSpec locations or required landing Attestations change.

**Migration**: All five carrier-closure scenarios move to Active ChangeContract Carrier Closure.

**Replacement**: Active ChangeContract Carrier Closure

### Requirement: Campaign Orchestration

**Reason**: Aggregate selection changes when the explicit selected base ChangeContract set or its dependencies change.

**Migration**: All three aggregate scenarios move to Selected ChangeContract Aggregate Predicate.

**Replacement**: Selected ChangeContract Aggregate Predicate

### Requirement: Campaign-terminal protected publication admission

**Reason**: Protected-publication admission changes with aggregate completion, source measurement, exact protected HEAD, and provider policy.

**Migration**: All six publication-admission scenarios move to Selected ChangeContract Protected-Publication Admission.

**Replacement**: Selected ChangeContract Protected-Publication Admission

### Requirement: Evolution Governance

**Reason**: Learning ledgers and practice records would create a third persistent semantic owner.

**Migration**: Every baseline scenario is retained under ChangeContract Hypotheses And Attested Learning with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: ChangeContract Hypotheses And Attested Learning

### Requirement: Evolution Ledger Protocol

**Reason**: Learning ledgers and practice records would create a third persistent semantic owner.

**Migration**: Every baseline scenario is retained under ChangeContract Hypotheses And Attested Learning with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: ChangeContract Hypotheses And Attested Learning

### Requirement: Evolution Ledger Single Source Of Truth

**Reason**: Learning ledgers and practice records would create a third persistent semantic owner.

**Migration**: Every baseline scenario is retained under ChangeContract Hypotheses And Attested Learning with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: ChangeContract Hypotheses And Attested Learning

### Requirement: Practice Evolution Kernel

**Reason**: Learning ledgers and practice records would create a third persistent semantic owner.

**Migration**: Every baseline scenario is retained under ChangeContract Hypotheses And Attested Learning with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: ChangeContract Hypotheses And Attested Learning

### Requirement: Practice Selection And Fate

**Reason**: Learning ledgers and practice records would create a third persistent semantic owner.

**Migration**: Every baseline scenario is retained under ChangeContract Hypotheses And Attested Learning with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: ChangeContract Hypotheses And Attested Learning

**Scenario replacement**: practice claim carries commitment effect -> practice proposition carries commitment effect

### Requirement: Executable Capability Parity Ledger

**Reason**: Comparison commands, schemas, roots, and tracked planes duplicate prove and Attestation.

**Migration**: Every baseline scenario is retained under Bounded Comparative Assurance Gate with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: Bounded Comparative Assurance Gate

**Scenario replacement**: Shadow parity records input identity -> Bounded Attestation binds proof inputs

**Scenario replacement**: Shadow parity rejects external false negatives -> Attestation records missing blocking gap

### Requirement: Parity evidence is committed before Work Lane proof

**Reason**: Comparison commands, schemas, roots, and tracked planes duplicate prove and Attestation.

**Migration**: Every baseline scenario is retained under Bounded Comparative Assurance Gate with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: Bounded Comparative Assurance Gate

**Scenario replacement**: parity-relevant Work Lane source makes generic evidence stale -> Changed proof input makes Attestation stale

**Scenario replacement**: evidence recording commit precedes proof and land -> Current Attestation is required before proof and land

### Requirement: Reference Adopter Parity Closure

**Reason**: Comparison commands, schemas, roots, and tracked planes duplicate prove and Attestation.

**Migration**: Every baseline scenario is retained under Bounded Comparative Assurance Gate with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: Bounded Comparative Assurance Gate

**Scenario replacement**: Reference adopter parity is closed -> Attestation establishes generic coverage

### Requirement: Shadow parity external execution honors checkout runtime topology

**Reason**: Comparison commands, schemas, roots, and tracked planes duplicate prove and Attestation.

**Migration**: Every baseline scenario is retained under Bounded Comparative Assurance Gate with ChangeContract, fresh RepositoryFacts, transient PlanIR, and Attestations as applicable.

**Replacement**: Bounded Comparative Assurance Gate

**Scenario replacement**: Stale root environment does not block current parity -> Checkout-bound execution substrate outranks stale environment

### Requirement: External Retirement Readiness

**Reason**: A dedicated profile-state lifecycle duplicates fresh RepositoryFacts
and Attestations.

**Migration**: The single baseline scenario moves to Attested Execution
Substrate Transition; present facts, comparative proof, exact effects, judgment,
and derived history retain their existing kernel owners.

**Replacement**: Attested Execution Substrate Transition

**Scenario replacement**: Retirement readiness is inspected -> Execution substrate transition is judged

### Requirement: Context-bound mutation admission

**Reason**: The accepted name is broader than the exact tracked-mutation
admission boundary carried by its scenarios.

**Migration**: All ten scenarios move to Exact Tracked Mutation Admission;
unchanged scenario titles map through the requirement replacement, and the one
renamed scenario maps explicitly below.

**Replacement**: Exact Tracked Mutation Admission

**Scenario replacement**: refresh-base resolves parity projection-only conflicts as stale projection -> refresh-base marks comparative-assurance Attestation stale after projection conflict

### Requirement: Work Lane Lifecycle Resolution

**Reason**: The duplicated requirement treats derived history as disposition authority and conflates local receipts with semantic effects.

**Migration**: The seven deduplicated lifecycle scenarios move to Exact Work Lane Lifecycle Effects.

**Replacement**: Exact Work Lane Lifecycle Effects

**Scenario replacement**: lane handoff is recorded as Chronicle resolution -> exceptional handoff is attested

**Scenario replacement**: orphan audit produces a decision, not a persistent orphan state -> unknown holder facts remain blocked observations

**Scenario replacement**: clean ownerless diverged source retires after semantic absorption -> linked retirement remains exact and holder-bound

**Scenario replacement**: exceptional cleanup consumes prior accepted judgment -> exceptional state does not widen lifecycle effects

**Scenario replacement**: break-glass reconciles after emergency action -> break-glass remains outside normal lifecycle

### Requirement: Preservation-bound exceptional Work Lane retirement

**Reason**: Preservation packages, Resolution decisions, and a dedicated exceptional retirement lifecycle create parallel semantic owners for facts already represented by Git, ChangeContract, RepositoryFacts, and Attestations.

**Migration**: Preserve dirty or uncertain content as ordinary Git-reachable recovery material; bind any irreversible disposition to the exact selected ChangeContract, fresh RepositoryFacts, and an accepted judgment Attestation; execute only `retire landed` or `retire superseded` under Exact Work Lane Lifecycle Effects.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Durable exceptional-resolution recovery inventory

**Reason**: A durable Resolution inventory and its reservation, decision, and receipt records are a third lifecycle truth plane.

**Migration**: Observe current refs, linked worktrees, Lease state, repository records, and recovery anchors as RepositoryFacts; represent accepted judgment and realized repository-semantic outcome as Attestations; derive history without a Resolution store.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Evidence-bound preservation-package clearing

**Reason**: A preservation-package clearing command and receipt store preserve the retired Resolution object model.

**Migration**: Recovery material follows repository-family record governance and is retained or superseded by exact record verification; no lifecycle command clears it as a semantic effect.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Dirty and unbound Work Lane content is preserved before destructive closeout

**Reason**: The requirement couples safety to a preservation-package and unbound-retirement mechanism that no longer exists.

**Migration**: Dirty, unknown, or owner-uncertain content remains blocked and recoverable through Git-reachable evidence or repository-family records; destructive effects are limited to exact linked `landed` or `superseded` retirement.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

**Reason**: Unbound-ref deletion is outside the terminal Work Lane lifecycle and duplicates native Git/ref recovery with a special command, Claim, Chronicle, and receipt plane.

**Migration**: Status reports unbound refs as observations only. ETHOS preserves and blocks them until an explicitly modeled future ChangeContract promotes a generic recovery transition; this release exposes no unbound retirement effect.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

**Reason**: The effect is inseparable from the retired unbound-resolution command and its parallel receipt records.

**Migration**: Remove the effect. Exact compare-and-swap remains only inside admitted linked Work Lane Lease, handoff, landing, and `landed|superseded` retirement transitions.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Ref-absent owner-unavailable partial effects are reconciled only through exact native lease CAS

**Reason**: Reconciliation exists only to recover a removed unbound-resolution transition and would retain that obsolete state machine.

**Migration**: Remove the transition and its records. Lease takeover remains the single exact, authorized holder-change mechanism; lost or partial external state stays blocked until modeled by a new generic ChangeContract.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Resolution Decisions and Receipts are semantically disjoint

**Reason**: Both types belong to the removed Resolution plane and duplicate judgment and effect Attestations.

**Migration**: Accepted judgment is a `judgment` Attestation; a realized repository-semantic mutation is an `effect` Attestation; ignored local coordination may retain non-semantic postcondition receipts.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Ownerless closeout admission is consumed at the effect boundary

**Reason**: Ownerless reservation, fence, decision, and completion receipt stores duplicate Lease/handoff authority and the terminal Attestation model.

**Migration**: Remove ownerless closeout. A current holder uses normal `landed|superseded` retirement; a foreign holder uses handoff or exact authorized Lease takeover; unknown ownership blocks mutation.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Authorized Work Lane cohort closeout is exact and evidence-bound

**Reason**: The historical cohort closeout carrier retains a separate decision,
preservation-package, and exceptional-effect lifecycle.

**Migration**: Observe cohort members as fresh RepositoryFacts. Absorb useful
meaning through the selected ChangeContract and current Attestations; use only
holder-bound handoff/takeover and the linked `landed` or `superseded` lifecycle.
Foreign, dirty, unknown, and unbound state remains observe-only and blocked.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Explicit conservative local-state maintenance

**Reason**: Orphan-lease pruning is a separate local-state effect owner rather
than part of the terminal Lease lifecycle.

**Migration**: Local coordination is observed from the current owned schema.
Missing, stale, or ambiguous state is preserved and blocked; this release does
not expose a generic local-state maintenance effect.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Recovery material is preservation-bound before cleanup

**Reason**: Chronicle-bound recovery cleanup retains the retired preservation and
Resolution receipt plane.

**Migration**: Recovery records are immutable repository-family records verified
by their own manifest and hash contract. Lifecycle commands do not clear them;
future cleanup requires a separately selected ChangeContract and Attestation.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Tracked lifecycle does not imply local-state maintenance effects

**Reason**: A separate maintenance apply and receipt lifecycle creates another
semantic effect plane.

**Migration**: Tracked lifecycle operations make no claim about ignored local
state. Any local-state effect must be independently admitted and attested under
the same terminal kernel.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Bounded Coordination Aggregate Detail State

**Reason**: Closeout-residue counters and residue records preserve a parallel
aggregate coordination state plane that is not a repository semantic owner.

**Migration**: Coordination readers expose fresh lane, lease, scope, and
content observations only. Detail is either `deferred` or freshly computed;
there is no closeout-residue inventory or lifecycle action derived from it.

**Replacement**: ChangeContract And Attestation Admission

### Requirement: Real history-residue effects use a distinct local closeout successor

**Reason**: A successor claim and external receipt create a parallel local-closeout
state machine after the historical carrier is archived.

**Migration**: Historical Git, OpenSpec, and records remain immutable. Current
work starts from a selected ChangeContract and fresh facts; no successor
closeout effect or unbound-lane recovery command is exposed.

**Replacement**: ChangeContract And Attestation Admission
