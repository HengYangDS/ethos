# ETHOS Adapters

## Purpose

ETHOS SHALL connect repository lifecycle semantics to provider-specific Git,
SQLite, process, package-manager, hosted CI, and protocol runtimes without
treating any provider as product truth.
## Requirements
### Requirement: Authorized Mutation
ETHOS SHALL block apply-mode land and publish unless authorization and expected
HEAD binding are explicit.

#### Scenario: Apply mode is requested
- **WHEN** `ethos land --apply` or `ethos publish --apply` runs
- **THEN** ETHOS requires explicit authorization and expected HEAD before any
  mutation can proceed

### Requirement: Work Lane Topology
ETHOS SHALL classify linked worktrees by lane role and surface foreign Work
Lanes without entering their file trees.

#### Scenario: Role policy is projected
- **WHEN** `ethos status --json` or `ethos lane status --json` reports
  workspace topology
- **THEN** the payload includes `role_policy`
- **AND** the role order is
  `release_root -> accepted_root -> candidate -> work_lane -> submit_lane`
- **AND** `branch_bindings` follow that semantic order before branch name
- **AND** host navigation labels are not product state
- **AND** adapters derive presentation from `worktree_binding` rather than
  owning branch, lane, or mutation semantics

#### Scenario: Foreign Work Lanes exist
- **WHEN** `ethos status` or `ethos lane status` inspects a repository with a
  linked `work/*` lane outside the current checkout
- **THEN** ETHOS reports the foreign lane path, branch, head, and role from git
  worktree metadata
- **AND** ETHOS reports `foreign_work_lane_present` as a required gap
- **AND** ETHOS does not read, modify, close, or clean the foreign lane

### Requirement: Prewrite Admission
ETHOS SHALL gate tracked writes through the current Work Lane role and editor
root binding before files are edited.

#### Scenario: Protected root write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from an accepted
  root, candidate, submit lane, detached checkout, or unknown lane
- **THEN** ETHOS blocks the request with `protected_lane_prewrite_blocked`

#### Scenario: Owned Work Lane write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane whose editor root matches the checkout root
- **THEN** ETHOS admits the write and returns a structured admission report

#### Scenario: Work Lane write lacks editor-root binding
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane without editor-root binding
- **THEN** ETHOS blocks the request with `editor_root_missing`

### Requirement: Lease-backed Lane Start
ETHOS SHALL acquire local lease records when creating Work Lanes through the
public lane command plane.

#### Scenario: Work Lane start is applied
- **WHEN** `ethos lane start <name> --apply --owner <owner>` runs from a clean
  accepted root and succeeds
- **THEN** ETHOS creates a `work/<name>` linked worktree
- **AND** ETHOS records an active lease in ignored local state under
  `.ethos/state/state.sqlite`
- **AND** raw Git worktree creation is not treated as standard ETHOS workflow
  state because it has no ETHOS lease or claim boundary

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --apply --owner <owner>` runs from an
  existing `work/*` lane or a dirty accepted root
- **THEN** ETHOS blocks the request with
  `lane_start_requires_clean_accepted_root`

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

### Requirement: Internal ETHOS Gate Fast Path
ETHOS SHALL execute internal ETHOS JSON gates in-process when safe.

#### Scenario: Internal gate runs without nested CLI process
- **WHEN** the local runner executes `python -m ethos.cli <command> --json`
- **THEN** ETHOS invokes the command plane in-process
- **AND** external provider commands still use the subprocess adapter

### Requirement: Official OpenSpec Lifecycle Adapter
ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
checks without replacing official OpenSpec validation.

#### Scenario: OpenSpec adapter reports lifecycle carriers
- **WHEN** ETHOS audits OpenSpec repository governance
- **THEN** the report includes official CLI command results
- **AND** the report includes active change carrier facts for proposal, design,
  tasks, delta specs, claim binding, and archive readiness

### Requirement: Work Lane Claim Binding Projection
ETHOS SHALL expose Work Lane ownership as claim boundary evidence for
trust-bearing mutation.

#### Scenario: Work Lane has a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane with a bound claim id
- **THEN** the lane report includes the claim id as boundary evidence
- **AND** the lane report does not mark the claim promoted by lane presence
  alone

#### Scenario: Work Lane lacks a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane without a bound claim id
- **THEN** the lane report remains usable for local work
- **AND** trust-bearing closeout reports a missing claim-binding gap

### Requirement: Intake Adapter Projection Boundary
ETHOS SHALL keep intake and Backlog provider state as projection or intake
evidence rather than repository truth.

#### Scenario: Intake provider reports done state
- **WHEN** an intake provider reports a task as complete
- **THEN** ETHOS records the intake state as projection evidence
- **AND** ETHOS still requires claim admission, OpenSpec lifecycle readiness,
  executed proof, and promotion targets before trust closeout
