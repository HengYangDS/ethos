## MODIFIED Requirements

### Requirement: Cross-host Handoff Adapter

ETHOS SHALL transfer content-addressed Git and context artifacts, never the
source SQLite lease. Preserved tracked and non-ignored untracked work SHALL be
restored before the destination lease is acknowledged, and partial imports
SHALL roll back branch and worktree residue.

#### Scenario: preserved handoff is imported safely

- **WHEN** a verified preserved handoff package is imported into a clean
  accepted-root clone
- **THEN** ETHOS creates a destination-local branch, worktree, and Lease
  generation
- **AND** restores tracked and non-ignored untracked content before acknowledgement
- **AND** rolls back branch and worktree state if restoration or lease creation fails.

### Requirement: Internal ETHOS Gate Fast Path

ETHOS SHALL execute gates that declare Python `providers` in-process and gates
that declare a `command` through the subprocess adapter.

#### Scenario: Internal gate runs without nested CLI process

- **WHEN** the local runner executes a gate that declares `providers`
- **THEN** ETHOS calls each declared provider in-process without a nested CLI
  process
- **AND** a gate that declares a `command` still uses the subprocess adapter

### Requirement: Protected ref hooks bind semantic evaluation to promoted control

ETHOS SHALL retain the accepted checkout as the fail-closed shell-hook boundary.
For candidate promotion, semantic ref admission SHALL run in a clean linked
checkout of the configured candidate at the exact promoted HEAD. Hooks SHALL
consume public closeout's prepared accepted-head decision, not reconstruct proof
or topology or require protected refs to equal the promoted object already.

#### Scenario: candidate control implementation differs from accepted checkout

- **GIVEN** the accepted checkout contains an older control implementation
- **AND** the configured candidate checkout is clean, bound to the configured
  candidate branch, and resolves to the promoted candidate head
- **AND** the candidate changes admission or proof-policy behavior
- **WHEN** official accepted-root closeout advances the accepted ref
- **THEN** the protected hook SHALL run the candidate-tree semantic evaluator
  against the candidate head
- **AND** it SHALL bind runner source, candidate checkout, candidate head, and
  transition fields explicitly
- **AND** it SHALL consume the same prepared ref intent and proof decision as
  closeout
- **AND** it SHALL not reject solely because accepted-old source would compute
  a different policy result.

#### Scenario: candidate semantic runner cannot be bound

- **WHEN** the configured candidate checkout is missing, dirty, detached,
  stale, or its semantic runtime cannot be bound to that checkout
- **THEN** the accepted-ref hook SHALL reject the transition
- **AND** it SHALL not fall back to accepted-old semantic source
- **AND** it SHALL project the complete public closeout command required to
  repair or retry the exact transition.

#### Scenario: changed managed shell hook bootstraps an accepted-to-release mirror

- **GIVEN** the candidate `.ethos/release.toml` declares `[release] mirror = "accepted_ff"`
- **AND** the candidate changes the tracked `reference-transaction` shell hook
- **AND** the incumbent shell can admit the accepted transition only through the
  candidate semantic runner
- **WHEN** official closeout performs the hook deployment bootstrap
- **THEN** it SHALL advance the accepted ref through an ordinary exact-intent,
  proof-bound compare-and-swap
- **AND** it SHALL synchronize the accepted checkout before advancing the
  release mirror through the promoted shell hook
- **AND** it SHALL not use a direct ref update, hook disablement, or hook-path
  override
- **AND** it SHALL report incomplete release-mirror bootstrap residue rather
  than accepted closeout when the second transition cannot complete.

#### Scenario: an exact protected object is pushed after local closeout

- **GIVEN** public closeout admitted and post-observed an exact signed candidate
  object through its prepared ref intent
- **WHEN** pre-push evaluates that same object for the declared protected role
- **THEN** the hook SHALL consume the admitted object and proof identity
- **AND** it SHALL not demand an additional hook-local role transition or a
  circular local-ref equality condition.

### Requirement: Adopter Release Metadata Remains Profile Bounded

ETHOS SHALL NOT infer product release semantics from the presence of a generic
tool configuration file, and SHALL read a release version only from a committed
`VERSION`, a `package.json` `version`, or a static `[project].version`, returning
missing, dynamic, malformed, or conflicting sources as structured gaps.

#### Scenario: Runtime-files adopter is audited

- **WHEN** an adopted repository has `pyproject.toml` without `[project]`, a
  `[tool.<name>]` table that declares `distribution = "runtime-files"`, and no
  `VERSION` file or `package.json` version
- **THEN** schema audits do not execute ETHOS product-only release policy
- **AND** direct release inspection reports `release_version_source_missing` as a
  structured gap, not a Python traceback
- **AND** invalid release-policy TOML is likewise returned as a structured gap

## REMOVED Requirements

### Requirement: Atomic Fresh Change Bootstrap

**Reason**: `start_change` was removed in `5efb74405`; `ethos lane start` takes no Change, and the command-plane spec has the official OpenSpec CLI author a Change inside an admitted lane.

**Migration**: Start a Work Lane with `ethos lane start`, then create the Change with the official OpenSpec CLI in that lane.
