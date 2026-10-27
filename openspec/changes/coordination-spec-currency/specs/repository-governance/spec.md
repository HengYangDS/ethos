## MODIFIED Requirements

### Requirement: Cohort-bound full Work Lane convergence

ETHOS SHALL treat a request to converge multiple Work Lanes as an exact,
observation-bound local program and SHALL NOT interpret a branch prefix or
session instruction as reusable wildcard authority.

#### Scenario: a convergence cohort is frozen before mutation

- **GIVEN** a maintainer requests convergence of multiple existing Work Lanes
- **WHEN** the program begins
- **THEN** a separate owned governance Work Lane records the exact branch, HEAD,
  worktree binding, dirty state, four-field Lease observation, intended
  retirement mode, and target-observation evidence for each lane
- **AND** later-created refs are outside the cohort unless separately admitted
- **AND** every effect recomputes mutable target facts before mutation.

#### Scenario: graph absorption does not erase a dirty overlay

- **GIVEN** a lane HEAD is equal to or an ancestor of accepted truth
- **AND** its linked worktree contains a dirty tracked or untracked delta
- **WHEN** convergence classifies the lane
- **THEN** landed and superseded retirement stay blocked with `work_lane_dirty`,
  and only a reviewed-content abandonment receipt can retire the lane
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
- **WHEN** the lane is resolved
- **THEN** a takeover consumes an accepted `lane-resolution:takeover`
  Attestation bound to the exact target and Lease generation, and irreversible
  retirement consumes one exact `ethos lane retire abandon` receipt
- **AND** the receipt's preview and its apply bind one exact observation
- **AND** dirty content is reviewed into that receipt before retirement
- **AND** a stale observation blocks the effect instead of falling back to raw
  Git deletion.

#### Scenario: local convergence completion keeps evidence planes separate

- **WHEN** all cohort intent has been integrated or explicitly superseded
- **THEN** strict carrier completion, HEAD-bound executed proof, candidate
  landing, accepted-root closeout, and lane retirement are verified as distinct
  transitions
- **AND** retained custody remains independent
- **AND** local completion does not claim remote push, hosted execution, or
  distribution publication.

### Requirement: Final declared-peer proposal absorption is proof-bound and non-destructive

When one or more declared peer proposal refs carry a final divergent patch,
ETHOS SHALL retain each exact observed proposal tip through ordinary merge
ancestry, execute local proof and governed local closeout before a protected
update, and delete a proposal ref only after the accepted peer branch contains
its tip or its accepted replacement and its review is observed as not open.

#### Scenario: Inputs move after a historical carrier archive

- **WHEN** a historical carrier has been archived but the candidate or a
  configured proposal ref advances before its unresolved lifecycle stages run
- **THEN** ETHOS SHALL preserve that archive as historical evidence
- **AND** bind a new official Change as the continuation before a new merge,
  proof, closeout, remote update, or proposal deletion is attempted
- **AND** the continuation SHALL re-observe the current inputs and retain its
  newly observed proposal tip through ordinary merge ancestry.

#### Scenario: Divergent proposal patch is reconciled

- **WHEN** a configured remote proposal ref is not an ancestor of the current
  candidate head
- **THEN** an owned Work Lane bound to the selected official Change records its
  exact tip and integrates it with an ordinary merge
- **AND** the resulting proposed head retains both the candidate and proposal
  histories as ancestors
- **AND** no force update, rebase, reset-based ref movement, or stash bypass is
  used.

#### Scenario: Publication follows local closeout

- **WHEN** the merged head has passed executed local proof and governed
  candidate/accepted closeout
- **THEN** publication persists one exact dry-run TransitionPlan and applies it
  as one atomic push with an exact lease for each protected ref
- **AND** remote ref observation and hosted-provider observation remain distinct
  from the local proof result
- **AND** a proposal ref is deleted only after the accepted peer branch contains
  its tip or accepted replacement and its review is observed as not open.

### Requirement: Versioned local-state schema evolution

ETHOS SHALL support only the current Lease schema: a `leases` table keyed by
`lane_ref` with `holder_ref`, a positive `generation` and `expires_at`, and
ownership limited to `leases`. Ordinary readers SHALL reject other shapes without
rewriting the database; only Git-common hook runtime activation migrates the
exact previous canonical shape. The database path SHALL derive from Git common-directory
identity; destructive linked retirement still requires the accepted checkout.

#### Scenario: A fresh state database is initialized

- **WHEN** no state schema exists
- **THEN** ETHOS creates the current Lease schema
- **AND** SQLite enforces one row per `lane_ref`
- **AND** it does not create a database-wide migration ledger.

#### Scenario: A version-1 state database is opened

- **WHEN** an ordinary reader opens a database whose `leases` table has a
  retired shape
- **THEN** ETHOS fails closed without translating or rewriting the database
- **AND** only Git-common hook runtime activation migrates the exact previous
  canonical shape, and only `ethos hook install --reset-state --authorize`
  applies the reset.

#### Scenario: Another owner shares the state database

- **WHEN** the current lease table coexists with tables owned by another
  local-state capability
- **THEN** lease initialization validates only its exact owned schema subset
- **AND** it preserves every unrelated table and row unchanged.

#### Scenario: A current database is initialized again

- **WHEN** the exact current Lease schema already exists
- **THEN** initialization is idempotent
- **AND** no active coordination row is rewritten or deleted.

#### Scenario: The accepted branch is not checked out

- **WHEN** another protected branch occupies the canonical repository path
- **THEN** a linked Work Lane reads the same Lease generation
- **AND** destructive retirement still requires its accepted-checkout control root.

### Requirement: Bounded Coordination Aggregate Detail State

ETHOS SHALL derive coordination aggregate detail state from the reader mode
selected by the caller, not from the number or contents of visible foreign Work
Lane rows.

#### Scenario: Empty bounded inventory remains deferred

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `ethos status --json` observes workspace status with foreign
  path-scope expansion disabled
- **THEN** `summary.coordination_detail_state` SHALL be `deferred`
- **AND** observable foreign-lane, unbound-lane, and missing-Lease counts SHALL
  remain available.

#### Scenario: Empty full inventory remains exact

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `ethos lane status --json` runs its full workspace observation
- **THEN** `summary.coordination_detail_state` SHALL be `exact`
- **AND** `dirty_foreign_work_lane_count` SHALL be zero.

### Requirement: Lease generation identity is complete across boundaries

Every status, handoff, retirement, receipt and effect SHALL bind a Lease by
exactly lane ref, holder ref, positive generation and expiry. Incomplete or stale
bindings SHALL fail. Lease SHALL NOT store another ID/fingerprint, Git coordinate,
Commitment, workflow field or outcome. Git HEAD/tree, package identity and effect
evidence SHALL remain independently bound by native facts, content identities
and Attestations.

#### Scenario: A boundary omits or changes a Lease fact

- **WHEN** an otherwise matching Lease binding omits or changes lane ref, holder
  ref, generation, or expiry
- **THEN** ETHOS rejects the handoff, retirement, or mutation effect
- **AND** the current Lease and Git carriers remain unchanged.

#### Scenario: Unavailable-holder recovery is admitted

- **WHEN** an accepted takeover authorization admits replacing one complete
  foreign Lease generation
- **THEN** ETHOS applies the same exact-generation transfer used by ordinary
  holder transfer
- **AND** no unavailable-holder wrapper or parallel destructive effect exists.

#### Scenario: Cross-host destination import is acknowledged

- **WHEN** the package target actor imports one verified handoff package
- **THEN** ETHOS creates one destination-local Lease generation
- **AND** its content-addressed acknowledgement binds the package identity and
  exact source Git facts separately from the destination lane ref, holder ref,
  generation, and expiry
- **AND** edited, incomplete, or non-target acknowledgements cannot authorize
  source revocation.

#### Scenario: Cross-host import fails after Lease acquisition

- **WHEN** destination restoration fails after the new Lease is acquired
- **THEN** ETHOS removes only the exact created Git carriers
- **AND** revokes only that exact Lease generation after carrier absence is
  proven
- **AND** uncertain compensation retains observable state and fails closed.

#### Scenario: The same content-addressed package is exported again

- **WHEN** the derived package directory already exists
- **THEN** ETHOS verifies and reuses the identical immutable package
- **AND** it never recursively deletes or replaces existing package content.

## ADDED Requirements

### Requirement: Mutation admission is bound to explicit repository context

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
- **AND** it resolves the named Work Lane ref as `binding_head` for the request's
  independent fresh Git-coordinate comparison
- **AND** ordinary writes bind the mutation request to current `HEAD` while the
  Lease remains the four-field lane-holder generation
- **AND** missing named refs, mismatched Git heads, accepted, candidate,
  proposal, other, and unknown detached branches remain protected and fail closed

#### Scenario: refresh-base keeps every replay conflict blocked

- **GIVEN** a clean Work Lane is stale behind the configured candidate branch
- **AND** replaying the Work Lane onto the candidate branch conflicts on any path
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

### Requirement: Work Lane lifecycle resolves from current facts

Routine lifecycle SHALL remain mechanically derived from current facts and exact
plans. A clean linked Work Lane whose exact HEAD equals or is an ancestor of the
current accepted HEAD SHALL be eligible for deletion-only landed retirement
without reconstructing historical proof, Commitment, or Lease authority.
Exceptional judgment SHALL be an exact authorized receipt or accepted
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing when a live Lease exists and
  postcondition Attestations for the applied effects
- **AND** no tracked decision record is required

#### Scenario: clean linked accepted residue retires without historical proof

- **WHEN** a named linked `work/*` Lane is clean and its exact HEAD equals or is
  an ancestor of the freshly observed accepted HEAD
- **AND** its ref, worktree binding, accepted ref, actor, and requested HEAD are
  unchanged at effect time
- **THEN** `ethos lane retire landed` SHALL remove only that exact worktree and
  branch through the existing exact-CAS effect owner
- **AND** it SHALL compile the deletion as a repository effect with no
  Commitment or proof-Attestation prerequisite
- **AND** it SHALL emit exact effect and postcondition evidence

#### Scenario: live Lease retains holder authority

- **WHEN** an otherwise retireable linked Lane has a valid Lease
- **THEN** only the exact current holder MAY apply landed retirement
- **AND** the Lease generation SHALL be re-observed and revoked exactly in the
  same bounded transition

#### Scenario: absent or expired Lease does not resurrect history

- **WHEN** an otherwise retireable linked Lane has no Lease or only an expired
  exact Lease row
- **AND** the invocation names a non-empty actor and explicitly authorizes the
  deletion-only transition
- **THEN** ETHOS SHALL respectively require the Lease to remain absent or revoke
  the exact expired row as the last effect, before the terminal receipt
- **AND** it SHALL NOT require Lease reacquisition, holder impersonation,
  historical proof, or a compatibility carrier

#### Scenario: unsafe retirement remains blocked

- **WHEN** the selected Lane is dirty, its HEAD is not accepted ancestry, its
  Lease state is unknown, a valid Lease belongs to another holder, or any exact
  Git, worktree, Lease, actor, or accepted coordinate drifts
- **THEN** retirement SHALL fail closed without deleting the branch or worktree
- **AND** no inventory entry, stale receipt, self-supplied holder, or historical
  relation SHALL substitute for the missing fact

#### Scenario: exceptional cleanup consumes an exact authorized receipt

- **WHEN** an exceptional destructive operation requires human judgment
- **THEN** it consumes one exact authorized receipt or accepted Attestation that
  names the exact target and disposition
- **AND** the operation re-observes mutable facts before its first effect

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, Lease, content, or recovery status is unknown or dirty
- **THEN** ETHOS preserves or blocks rather than inferring authority
- **AND** irreversible deletion requires one exact authorized receipt and
  evidence

#### Scenario: lane handoff is recorded as a package and effect Attestation

- **WHEN** a Work Lane is handed off
- **THEN** it is recorded as a content-addressed handoff package and an
  `effect:handoff-package` Attestation, not Chronicle
- **AND** it does not replace the destination-local Lease

#### Scenario: missing holder evidence creates no persistent orphan state

- **WHEN** a lane has missing or ambiguous holder evidence
- **THEN** orphan-like facts remain observations, and the lane's disposition is
  an exact retirement receipt or an accepted takeover
- **AND** no persistent orphan or Chronicle state is created

#### Scenario: clean ownerless diverged source retires through reviewed abandonment

- **WHEN** a clean diverged Work Lane has no valid Lease
- **THEN** `ethos lane retire abandon --review-content` re-observes the source at
  apply, and its exact ref deletion emits an effect Attestation
- **AND** the authority does not extend to another lane or remote effect

### Requirement: Work Lane base refresh reports success only on candidate ancestry

ETHOS SHALL report a successful Work Lane base refresh only when the candidate
HEAD captured before replay is an ancestor of the reported refreshed Work Lane
HEAD.

#### Scenario: zero-code replay leaves the Work Lane unrefreshed

- **GIVEN** a clean owned Work Lane is stale behind the configured candidate
  branch
- **AND** the replay subprocess returns zero without making the captured
  candidate HEAD an ancestor of the Work Lane HEAD
- **WHEN** `ethos lane refresh-base --apply --authorize --expect-head <head>
--json` evaluates the replay result
- **THEN** ETHOS reports `state=blocked`
- **AND** it reports `refresh_base_postcondition_failed`
- **AND** it does not report `base_refreshed` or offer landing as the next
  lifecycle transition.

### Requirement: Handoff contracts reject coercion and ambiguous object IDs

Handoff contracts SHALL reject coercive scalar values and Git object IDs whose
width is not exactly 40 or 64 hexadecimal characters.

#### Scenario: A wire payload relies on coercion or an ambiguous object ID

- **WHEN** a handoff payload supplies a boolean as an integer, a Lease generation
  as a string or boolean, or a Git object ID of intermediate width
- **THEN** both the typed contract and its JSON Schema boundary reject it
- **AND** no lifecycle effect begins.

### Requirement: Work Lane cohort retirement binds each exact target

Authorized cohort retirement SHALL evaluate each observed lane and SHALL NOT
grant wildcard foreign-lane authority. Before supersession or retirement, its
TransitionPlan SHALL bind branch and HEAD, the accepted HEAD, the four-field
Lease observation when present, worktree cleanliness, and the retirement mode.
Any target drift invalidates the prepared receipt.

#### Scenario: A visible foreign lane is not wildcard authority

- **WHEN** an owned carrier audits a visible foreign Work Lane
- **THEN** it records an exact target observation and allows only the native
  holder-bound or accepted exceptional lifecycle path for that target
- **AND** it does not allow a batch, wildcard, or stale observation to write,
  land, retire, or delete a different foreign Work Lane.

#### Scenario: A moving target invalidates its receipt

- **WHEN** a target's head, dirty state, holder, Lease generation, or relation
  to accepted truth changes after its receipt was prepared
- **THEN** ETHOS blocks the worktree and branch deletion that the receipt planned
- **AND** the owned carrier re-observes the target before preparing a new
  receipt.

#### Scenario: Historical source is absorbed without historical topology

- **WHEN** a recovered Work Lane exposes behavior absent from the current
  contract
- **THEN** an owned current-baseline lane adds the smallest focused regression
  and implementation for that behavior
- **AND** its executed proof and accepted closeout identify the source lane as
  absorbed behavior, not as a merged historical branch
- **AND** only a later fresh native retirement transition may remove the source
  lane.

#### Scenario: Current-equivalent or deferred intent is not silently erased

- **WHEN** a source lane's behavior is already covered by accepted source and
  proof, or its proposal is outside the current product decision
- **THEN** the absorption record names the current proof or deferred decision
- **AND** it keeps the source lane intact until an exact retirement or later
  product/adopter admission path is separately established.

#### Scenario: A lane with no missing behavior retires without integration

- **WHEN** an exact review classifies every patch-inequivalent change of a
  historical Work Lane as accepted, superseded, obsolete, or intentionally
  deferred
- **THEN** the lane is retired rather than merged, rebased, refreshed, or landed
- **AND** retirement uses one exact `ethos lane retire abandon` receipt that
  binds the accepted HEAD, the target HEAD and tree, any reviewed worktree
  content, and the four-field Lease observation when present
- **AND** any later accepted, target, or Lease drift blocks worktree and branch
  deletion until a new observation and receipt exist.

### Requirement: Dirty and unbound Work Lane content is retired only through an exact reviewed receipt

ETHOS SHALL NOT irreversibly retire a dirty Work Lane or a diverged unbound Work
Lane reference without one exact retirement receipt persisted before any
destructive effect. The receipt SHALL record the exact target head and tree, the
accepted head, the reviewed content manifest when content is reviewed, and the
retirement mode and reason. A clean accepted-absorption finding alone SHALL NOT
discard an unreviewed dirty overlay.

#### Scenario: A dirty lane needs a reviewed-content receipt

- **WHEN** a full lane observation reports a Work Lane with tracked, deleted,
  conflicted, or untracked content
- **THEN** landed and superseded retirement stay blocked with `work_lane_dirty`
- **AND** only an `ethos lane retire abandon --review-content` receipt, persisted
  before any destructive effect, can retire the lane.

#### Scenario: A diverged unbound ref is not deleted for lacking a worktree

- **WHEN** an unbound Work Lane ref diverges from accepted truth
- **THEN** its retirement requires an exact abandonment receipt
- **AND** ETHOS does not delete the ref merely because it lacks a linked
  worktree.

## REMOVED Requirements

### Requirement: Context-bound mutation admission

**Reason**: Its scenario "refresh-base resolves parity projection-only conflicts as stale projection" names a recovery removed from `src/ethos/adapters/mutation/lane_lifecycle/refresh.py` in `3d393c93a`; every conflicting replay now aborts. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Mutation admission is bound to explicit repository context", which keeps the other scenarios and merges the two refresh-base conflict scenarios into "refresh-base keeps every replay conflict blocked".

### Requirement: Work Lane Lifecycle Resolution

**Reason**: Its scenario "lane handoff is recorded as Chronicle resolution" contradicts its own body and the requirement text; the Chronicle owner `src/ethos/adapters/mutation/resolution/chronicle.py` was deleted in `ed18713a0`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Work Lane lifecycle resolves from current facts". It states exceptional judgment as an exact authorized receipt or accepted Attestation, records a handoff as a package and effect Attestation, retires an ownerless source through reviewed abandonment, and drops the break-glass scenario, whose predeclared Commitment and reconciliation no code implements; the PDC's bounded maintainer recovery owns that path.

### Requirement: Work Lane refresh success is ancestry-bound

**Reason**: Its scenario "parity-projection recovery preserves the same success condition" names a recovery removed from `src/ethos/adapters/mutation/lane_lifecycle/refresh.py` in `3d393c93a`. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Work Lane base refresh reports success only on candidate ancestry".

### Requirement: Resolution Decisions and Receipts are semantically disjoint

**Reason**: Lane-resolution Decisions and completion Receipts, including `decision_id`, were deleted with `src/ethos/adapters/mutation/resolution/` in `ed18713a0`; its scenario "A resolution effect completes" has no subject. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Handoff contracts reject coercion and ambiguous object IDs" for the surviving handoff contracts.

### Requirement: Authorized Work Lane cohort closeout is exact and evidence-bound

**Reason**: Its scenario "Zero missing behavior selects preservation closeout, not integration" names the lane-resolution `preserve-retire` decision and recovery packages, deleted with `src/ethos/adapters/mutation/resolution/` in `ed18713a0`; retirement now consumes an exact `ethos lane retire abandon` receipt and preserves no content. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Work Lane cohort retirement binds each exact target", which keeps the other scenarios and renames "A moving target invalidates its decision" to "A moving target invalidates its receipt".

### Requirement: Dirty and unbound Work Lane content is preserved before destructive closeout

**Reason**: ETHOS no longer preserves reviewed content: `src/ethos/adapters/mutation/lane_retirement/content.py` checks it against a hash manifest and removes it, and only the receipt survives. The title and both scenarios describe a preservation package.

**Migration**: Replaced by the requirement "Dirty and unbound Work Lane content is retired only through an exact reviewed receipt".
