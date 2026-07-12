# ETHOS Adapters

## Purpose

ETHOS SHALL connect repository lifecycle semantics to provider-specific Git,
SQLite, process, package-manager, hosted CI, and protocol runtimes without
treating any provider as product truth.
## Requirements
### Requirement: Exact-request Mutation Admission
ETHOS SHALL block apply-mode land and publish unless execution confirmation,
expected HEAD binding, applicable Commitments, current facts, and required
Evidence admit the exact request. Confirmation SHALL NOT authenticate a caller
or create reusable authorization.

#### Scenario: Apply mode is requested
- **WHEN** `ethos land --apply` or `ethos publish --apply` runs
- **THEN** ETHOS requires explicit confirmation and expected HEAD before any
  mutation can proceed
- **AND** the decision binds action, resource, expected state, policy refs,
  evidence refs, and decision basis
- **AND** it mints no role, token, session, or reusable permission.

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
- **AND** ETHOS reports `foreign_work_lane_present` as a coordination signal
- **AND** ETHOS does not read, modify, close, or clean the foreign lane
- **AND** ETHOS reports a non-authoritative action preview with observe as the
  only candidate action and write, land, and retire blocked
- **AND** actual mutation re-evaluates its exact current request.

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
- **WHEN** `ethos lane start <name> --apply --holder-ref <holder-ref>` runs from a clean
  accepted root and succeeds
- **THEN** ETHOS creates a `work/<name>` linked worktree
- **AND** ETHOS records an active lease in ignored local state under
  `.ethos/state/state.sqlite`
- **AND** raw Git worktree creation is not treated as standard ETHOS workflow
  state because it has no ETHOS lease or claim boundary

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --apply --holder-ref <holder-ref>` runs from an
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

### Requirement: Bounded External Evidence Adapters

ETHOS SHALL verify external identity assertions, hosted-enforcement receipts,
and control-replacement verifier receipts only when the applicable Commitment
requires them. Adapters SHALL store no credentials and SHALL NOT mint
authority. Optional provider-local reference implementations SHALL live in a
declared extension bundle, never in an unowned root-level adapter directory.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires a receipt outside the candidate tree binding both
  heads, both control digests, verifier digest, candidate proof, and bootstrap
  Chronicle decision
- **AND** the candidate proof is a native executed `ethos prove --execute --json`
  result with `command = "prove"`, `ok = true`, `state = "proven"`,
  `data.executed = true`, and matching candidate HEAD bindings in
  `data.evidence.head` and `data.provenance.predicate.head`
- **AND** a hand-authored `{head, state}` envelope is not accepted as candidate
  proof
- **AND** missing or unverifiable provenance returns `defer`.

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention for a ref transition
- **THEN** a provider receipt binds the exact action, resource, old value, new
  value, observation, coverage, and receipt digest
- **AND** local hooks or provider configuration alone do not prove prevention.

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** ETHOS ships the default-off independent-verification reference source
- **THEN** it resides at
  `extensions/independent-verification/adapters/independent_identity/reference_verifier.py`
- **AND** its manifest, documentation, and focused tests are colocated in that
  extension bundle
- **AND** no root-level `reference_adapters/` source, forwarding module, or
  compatibility alias remains
- **AND** the extension does not create an adopter policy, account, key,
  network, daemon, or scheduling requirement.

### Requirement: Cross-host Handoff Adapter

ETHOS SHALL transfer content-addressed Git and context artifacts, never the
source SQLite lease. Preserved tracked and non-ignored untracked work SHALL be
restored before the destination lease is acknowledged, and partial imports
SHALL roll back branch and worktree residue.

#### Scenario: preserved handoff is imported safely

- **WHEN** a verified preserved handoff package is imported into a clean
  accepted-root clone
- **THEN** ETHOS creates a destination-local branch, worktree, lane incarnation,
  and lease
- **AND** restores tracked and non-ignored untracked content before acknowledgement
- **AND** rolls back branch and worktree state if restoration or lease creation fails.

### Requirement: Internal ETHOS Gate Fast Path
ETHOS SHALL execute internal ETHOS JSON gates in-process when safe.

#### Scenario: Internal gate runs without nested CLI process
- **WHEN** the local runner executes `python -m ethos.cli <command> --json`
- **THEN** ETHOS invokes the command plane in-process
- **AND** external provider commands still use the subprocess adapter

### Requirement: Official OpenSpec Lifecycle Adapter

ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
review and SHALL preflight an active change's archiveability through an isolated
official archive projection before proof, land, or accepted-root closeout.

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

### Requirement: Lifecycle Review Covers Active Changes

ETHOS SHALL review all active OpenSpec changes in lifecycle mode when no single
change is explicitly selected.

#### Scenario: Multiple active changes are reviewed

- **WHEN** `ethos openspec --lifecycle --json` runs without `--change`
- **THEN** lifecycle output includes every active change reported by official
  OpenSpec list output
- **AND** each change is checked for carriers, claim binding, proposal metadata,
  capability profile health, and out-of-scope boundaries.

### Requirement: Optional tool adapters remain replaceable
ETHOS SHALL expose optional adapter boundaries for environment runners, graph
systems, task ledgers, external workflow frameworks, and agent method packs
without making them product substrate. Useful external practices MAY be mapped
to ETHOS contracts, adapters, evidence classes, projections, or method packs
only through accepted governance changes that keep lifecycle truth inside the
ETHOS kernel contract.

#### Scenario: Adapter profile is reported

- **WHEN** `ethos quality tool-profiles --json` reports tool adapters
- **THEN** Nox, Pixi, Pants, task-ledger, and agent-method-pack entries SHALL be
  visible as adapter-only boundaries
- **AND** their output SHALL NOT replace ETHOS proof, OpenSpec lifecycle checks,
  claims, evidence, or Git-native Work Lane semantics.

#### Scenario: External workflow frameworks are classified
- **WHEN** ETHOS evaluates Comet, Spec Kit, BMAD, Superpowers, Task Master, Agent OS, OpenSPDD, Shotgun, or fspec
- **THEN** their useful practices may be mapped to ETHOS contracts, adapters, evidence classes, projections, or method packs
- **AND** their command planes, hidden state directories, task stores, and phase names do not become ETHOS lifecycle truth by default
