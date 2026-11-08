## MODIFIED Requirements

### Requirement: Linked Work Lane retirement has one exact effect

Landed and superseded retirement SHALL share one strict request and owner,
binding actor, mode, lane ref/HEAD, clean linked path and accepted ref/HEAD.
Consumed Leases SHALL bind only lane ref, holder, generation and expiry under
SQLite transaction; Git facts remain independent. Remove only the selected clean
checkout and compare-delete its exact ref in a transaction verifying accepted.

#### Scenario: Landed preview supplies an executable exact continuation

- **WHEN** an admitted preview selects one landed branch without an expected HEAD
- **THEN** its next command binds that branch's observed HEAD, not accepted's HEAD
- **AND** executing it rechecks all current admission and exact-effect conditions
- **AND** an explicitly supplied expected HEAD is preserved, never silently replaced

#### Scenario: Integration continuation follows Git containment

- **WHEN** a Work Lane HEAD is already contained in the candidate but not accepted
- **THEN** lane status selects accepted closeout instead of repeating land
- **WHEN** the Work Lane HEAD is contained in accepted
- **THEN** lane status selects the existing landed-retirement preview
- **AND** retirement still reviews nontracked content and rechecks exact authority
- **AND** an absent candidate does not turn already accepted content into an
  authoring or coordination failure
- **AND** uncommitted lane content remains authoring work, not a retirement cue
- **AND** a lane ahead of candidate continues to select land

#### Scenario: Nontracked content requires an explicit disposition

- **WHEN** a linked worktree contains nontracked content, including ignored evidence
- **THEN** automatic retirement preserves the worktree, refs, Lease and content
- **AND** the preview reports its native footprints and existing lifecycle labels
- **AND** neither Git ignore rules nor a lifecycle label authorize deletion
- **AND** continuation requests existing exact content review before separately authorized disposal
- **AND** required custody is preserved outside the retiring resource before disposal

#### Scenario: Nontracked content appears after planning

- **WHEN** ignored content appears before an unreviewed retirement effect or receipt recovery
- **THEN** fresh effect admission refuses deletion and selects a new content review
- **AND** a reviewed receipt still refuses changed content, foreign ownership and active consumers

#### Scenario: Reviewed content remains inspectable without repeating its manifest

- **WHEN** an owned lane's reviewed tree contains many generated and nontracked nodes
- **THEN** the public preview gives its exact receipt and bounded review summary, not a second copy of the complete manifest
- **AND** the receipt binds a content-addressed manifest by its digest and per-root totals
- **AND** the manifest retains every reviewed node for inspection and effect-time drift checks
  until the operation is terminal and no request without a terminal receipt binds it
- **AND** the summary alone never authorizes disposal

#### Scenario: Unrelated native file-descriptor churn is not a retirement consumer

- **WHEN** unrelated processes close descriptors during selected content retirement
- **THEN** the native observer scopes its search to the worktree and external Git index
- **AND** cwd, file, mapping, writer, hardlink and index holders still block deletion
- **AND** an already absent reviewed worktree is not a deletion target; its surviving index remains observed
- **AND** an observation that an unreadable record leaves incomplete is taken again, at most three times within the observer's one 30-second timeout
- **AND** a present unsafe worktree, missing index, incomplete output, a permission failure inside an otherwise inspected process, or a timeout remains unknown
- **AND** reviewed content is rechecked after the process observation

#### Scenario: Processes outside the inspection boundary are reported, not hidden

- **WHEN** a content admission observes open files while processes the invoking user may not inspect are running
- **THEN** the observation covers only the processes the invoking user may inspect
- **AND** a process that denies every `/proc` entry the observer reads, its descriptor links and threads' entries included, is reported once as uninspectable by process ID, user ID and command, not as a consumer
- **AND** where the platform omits uninspectable processes without a record, the report marks their list unavailable rather than empty
- **AND** each content admission records its observation in the progress it produces
- **AND** the terminal receipt and result carry the observation of the admission that removed the worktree, including after recovery

#### Scenario: Exact Lease observation changed after planning

- **WHEN** a planned live or expired Lease differs in lane ref, holder ref,
  generation, or expiry at effect time
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current Lease intact.

#### Scenario: A Lease appears after an absent observation

- **WHEN** landed retirement planned against an absent Lease and a row for the
  target lane exists when the SQLite transaction re-observes it
- **THEN** ETHOS blocks the effect
- **AND** it does not delete the linked worktree, branch, or new Lease.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite Lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS re-observes the ref, worktree, and Lease postconditions
- **AND** it reports the exact non-terminal state without claiming retirement.

### Requirement: Dirty and unbound Work Lane content is retired only through an exact reviewed receipt

ETHOS SHALL NOT irreversibly retire a dirty Work Lane or a diverged unbound Work
Lane reference without one exact retirement receipt persisted before any
destructive effect. The receipt SHALL record the exact target head and tree, the
accepted head, the digest and per-root totals of any reviewed content manifest,
and the retirement mode and reason. A clean accepted-absorption finding alone SHALL NOT
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

### Requirement: Destructive Work Lane retirement is a resumable observed transition

Authorized retirement SHALL be one receipt-bound transition over exact worktree,
ref and Lease. Before effects, persist the immutable request and verify surviving
control root, Git binary, every process cwd, ref/HEAD, cleanliness, Lease and actor
authority. After each attempt, native observations SHALL determine completed and
remaining effects, not process flags. Revoke Lease only after worktree/ref absence.

#### Scenario: Execution coordinates fail before destruction

- **WHEN** Git cannot be resolved or the surviving control root and effect
  working directories cannot be used before an authorized retirement
- **THEN** ETHOS blocks before removing the worktree, branch ref, or Lease
- **AND** the structured result identifies the failed preflight coordinate.

#### Scenario: Failure follows worktree removal

- **WHEN** the exact worktree is removed and a later ref effect cannot start or
  complete
- **THEN** ETHOS reports `state=partial_transition`
- **AND** the durable progress receipt reports worktree removal as complete and
  ref deletion and Lease revocation as remaining
- **AND** no later process is launched from the removed worktree.

#### Scenario: Recovery converges from native carrier facts

- **WHEN** an authorized caller supplies an exact current retirement receipt
  after a partial effect
- **THEN** ETHOS re-observes the surviving control root, ref, worktree, and Lease
- **AND** it applies only the effects still required for the declared terminal
  state
- **AND** a repeated recovery of the same terminal request is recognized as
  complete without a second destructive effect
- **AND** a request that still carries its reviewed nodes inline continues
  through a fresh admission derived from its coordinates.

#### Scenario: Recovery authority or coordinates are ambiguous

- **WHEN** the request bytes, repository identity, target HEAD, accepted
  authority, or caller authority differ from the receipt, or a valid Lease is
  held by another actor
- **THEN** ETHOS fails closed without changing any carrier
- **AND** it does not reinterpret an old receipt or mint replacement authority.
