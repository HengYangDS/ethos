# Spec Delta

## ADDED Requirements

### Requirement: Exact Index-target Prewrite Admission

ETHOS SHALL evaluate an exact index-target patch through the existing staged
admission owner, independently of working-file bytes. The decision SHALL bind
the observed index tree and exact preimage for compare-and-swap at the actual
staging boundary; it SHALL NOT execute staging or create reusable authority.

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
- **AND** the decision is non-reusable and requires fresh expected-state
  comparison at the actual staging effect.

#### Scenario: Real index preimage becomes stale

- **WHEN** the real index changes during evaluation or no longer matches the
  expected prestate at the actual effect boundary
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
- **AND** the prospective tree remains a content identity rather than a retained
  artifact or permission for a later staging request.
