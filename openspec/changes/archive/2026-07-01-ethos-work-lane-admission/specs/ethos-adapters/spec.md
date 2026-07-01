## ADDED Requirements

### Requirement: Work Lane Topology
ETHOS SHALL classify linked worktrees by lane role and surface foreign Work
Lanes without entering their file trees.

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
  root, candidate, submit branch, detached checkout, or unknown lane
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

#### Scenario: Work Lane start is requested from a non-accepted or dirty root
- **WHEN** `ethos lane start <name> --apply --owner <owner>` runs from an
  existing `work/*` lane or a dirty accepted root
- **THEN** ETHOS blocks the request with
  `lane_start_requires_clean_accepted_root`

### Requirement: Admission Before Product Audit
ETHOS SHALL evaluate apply-mode mutation admission before running product
self-audit checks.

#### Scenario: Apply mode is blocked by lane admission
- **WHEN** `ethos land --apply` or `ethos publish --apply` is invoked from a
  protected root with explicit authorization and expected HEAD
- **THEN** ETHOS returns structured `blocked` JSON with
  `protected_root_mutation`
- **AND** ETHOS does not require the target repository to contain ETHOS product
  self-governance schemas before reporting the admission failure
