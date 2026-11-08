# Spec Delta

## ADDED Requirements

### Requirement: Exact Index-target Prewrite Admission

ETHOS SHALL evaluate an exact index-target patch through the existing staged
admission owner, independently of working-file bytes. The decision SHALL bind
the observed real index tree and exact preimage separately from the prospective
tree; it SHALL NOT execute staging or create reusable authority.

#### Scenario: Index-only patch preserves mixed content

- **GIVEN** an owned lane has different index and working-file bytes plus
  unrelated staged paths
- **WHEN** `ethos lane prewrite --patch <file> --target index` evaluates a valid
  exact patch whose preimage matches the observed index
- **THEN** it checks the patch with native cached patch checking and evaluates
  the prospective staged tree through the existing admission owner
- **AND** the real index, worktree, every other staged path, shared object store,
  refs and Lease remain unchanged.

#### Scenario: Decision binds the observed mutable prestate

- **WHEN** an exact index preview returns its decision
- **THEN** the request binds the observed real index tree, exact index preimage,
  HEAD, current Lease, patch and effect paths separately from the prospective tree
- **AND** it exposes the expected real index tree and preimage digest for the
  caller without claiming enforcement at the later native staging effect
- **AND** the existing commit staged admission re-admits the actual staged content.

#### Scenario: Real index preimage becomes stale

- **WHEN** reobservation detects that the real index changed during evaluation
- **THEN** ETHOS refuses the stale request with a dedicated index-preimage gap
- **AND** it does not overwrite or restore the concurrent writer's state.

#### Scenario: Default target and required facts remain explicit

- **WHEN** the caller omits `--target index`, omits the exact patch or paths, or
  lacks observable index state or current lane authority
- **THEN** worktree remains the default and missing or conflicting inputs fail
  closed under the existing admission contract
- **AND** no working bytes are silently staged and no earlier decision supplies
  the missing authority.

#### Scenario: Candidate custody ends with the preview

- **WHEN** the preview passes, refuses or fails during observation
- **THEN** every staged candidate reader uses the same isolated candidate
  environment and the owned temporary index and objects are removed
- **AND** repository Git writes, refs and lifecycle effects never receive the
  candidate environment
- **AND** the prospective tree remains a content identity rather than a retained
  artifact or permission for a later staging request.

#### Scenario: Staged reader loses candidate custody

- **WHEN** a staged reader cannot observe the prospective tree because its
  candidate environment was not supplied
- **THEN** it fails closed without substituting working-file bytes.

#### Scenario: Index form has no complete observable prestate

- **WHEN** the real index is split or its lock is present
- **THEN** the preview returns unknown with a specific unavailable or locked gap
- **AND** it preserves the index, shared part and lock.

#### Scenario: Native cached apply handles a sparse index

- **WHEN** native cached patch checking and application succeed on a disposable
  copy of a sparse index
- **THEN** ETHOS evaluates that prospective tree through the same staged owner
- **AND** the real sparse index and working-file state remain unchanged.
