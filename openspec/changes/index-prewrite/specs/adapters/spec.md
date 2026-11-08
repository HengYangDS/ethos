# Spec Delta

## MODIFIED Requirements

### Requirement: Prewrite Admission

ETHOS SHALL admit tracked authoring only from an owned `work/*` lane.

#### Scenario: Protected root write is requested

- **WHEN** `ethos lane prewrite` checks tracked candidate paths from an accepted
  root, candidate, detached checkout, or other non-Work-Lane checkout
- **THEN** ETHOS blocks the request with `protected_lane_prewrite_blocked`.

#### Scenario: Owned Work Lane write is requested

- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane whose editor root matches the checkout root
- **THEN** ETHOS admits the write and returns a structured admission report.

#### Scenario: Work Lane write lacks editor-root binding

- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane without editor-root binding
- **THEN** ETHOS blocks the request with `editor_root_missing`.

#### Scenario: Proposal ref is checked out locally

- **WHEN** `ethos lane prewrite` evaluates tracked mutation from a `proposal/*` checkout
- **THEN** the checkout has no authoring role
- **AND** ETHOS blocks the write rather than suggesting that the proposal ref is a Work Lane.

#### Scenario: Exact index patch preserves mixed content

- **GIVEN** an owned lane has unrelated staged and unstaged content
- **WHEN** prewrite evaluates an exact text patch with `--target index`
- **THEN** it evaluates the prospective staged bytes without changing the real
  index, shared object store, worktree, refs or Lease
- **AND** it binds the exact requested paths, patch, HEAD, Lease, real index
  prestate and prospective tree in its non-reusable admission decision.

#### Scenario: Worktree remains the default target

- **WHEN** a caller omits the target for a patch whose preimage exists only in
  the index
- **THEN** prewrite refuses the worktree preimage mismatch
- **AND** it does not silently select the index or stage whole files.

#### Scenario: Index request lacks exact scope or observable state

- **WHEN** an index request lacks a patch, has different native patch paths,
  or cannot observe its real index or prospective tree
- **THEN** it fails closed and reports the exact missing or conflicting input
- **AND** real staging and working files remain unchanged.

#### Scenario: Candidate object lifetime ends

- **WHEN** an index preview passes, refuses, or its observer raises an error
- **THEN** its temporary index and candidate object directory are removed
- **AND** every candidate reader uses the same isolated object environment
- **AND** the returned prospective tree is a content identity, not a retained
  artifact or permission to reuse a previous admission.

#### Scenario: Index patch relocates a path

- **WHEN** an index patch renames or copies a tracked path
- **THEN** the exact request includes both its native source and destination
- **AND** an omitted source path cannot inherit postimage-only admission.

#### Scenario: Working-tree symlink differs from the index

- **GIVEN** the index contains a regular tracked path whose working-tree entry
  is an unrelated symlink
- **WHEN** prewrite evaluates an exact index patch for that lexical path
- **THEN** it evaluates the staged identity without following the symlink
- **AND** outside-root paths and parent traversal remain invalid.

#### Scenario: Real prestate changes during index admission

- **WHEN** the real index or HEAD changes while an index patch is evaluated
- **THEN** prewrite refuses the stale decision even if its disposable index
  remains unchanged
- **AND** it preserves the concurrent writer's state and removes only its own
  temporary preparation.

#### Scenario: Authority changes during staged admission

- **WHEN** staged admission observes a different effective lane, invocation
  actor, Lease holder, generation or expiry after material-scope evaluation
- **THEN** it refuses the stale authority instead of inheriting the earlier pass
- **AND** an unchanged owned-rebase context retains its existing lane identity.
