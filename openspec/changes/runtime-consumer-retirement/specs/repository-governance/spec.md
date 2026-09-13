## MODIFIED Requirements

### Requirement: Git-common hook runtime activation is singular

ETHOS SHALL maintain one effective hook generation and one selected immutable
runtime per Git common directory. The invoking repository authority SHALL
validate a candidate runtime and hook bundle before atomically replacing the
runtime selector and common hook activation. Linked worktrees SHALL consume
that common selection without interpreting historical launchers or profiles as
another runtime authority.

#### Scenario: One install converges all linked worktrees

- **GIVEN** linked worktrees resolve different generated hook generations
- **WHEN** the public hook installation command succeeds
- **THEN** repository-common Git config owns the effective `core.hooksPath`
- **AND** the Git-common runtime selector identifies the one runtime used by every installed hook and package-only remediation command
- **AND** owned worktree-local activation overrides are absent.

#### Scenario: Cleanup preserves every observed consumer

- **WHEN** hook/runtime cleanup evaluates generated generations
- **THEN** it retains the selected runtime and every generation referenced by effective config, live process commands or native linked interpreter bindings
- **AND** historical operation and diagnostic records do not create executable dependencies merely by naming a generation
- **AND** current operation recovery consumes the selected runtime rather than treating historical observations as activation authority.

#### Scenario: Historical linked checkout cannot veto current activation

- **GIVEN** the invoking repository resolves a valid accepted runtime source identity
- **AND** a linked historical checkout contains an obsolete or invalid profile
- **WHEN** the public hook installation command runs from the invoking repository
- **THEN** every linked worktree validates the same common activation and selected runtime against the invoking repository's exact source identity
- **AND** the historical profile does not select or veto that identity
- **AND** unreadable Git configuration, selector, or runtime projection still fails closed.

#### Scenario: activation validation fails

- **WHEN** the candidate runtime, manifest, entrypoint, or generated hook bundle fails validation
- **THEN** neither the runtime selector nor effective common hook activation changes
- **AND** the previously selected valid runtime remains the sole selected runtime.

## ADDED Requirements

### Requirement: Generation reclamation uses fresh operational facts

ETHOS SHALL reclaim only exact owned generations without current operational
dependencies. Every destructive step SHALL recheck dependency observations and
directory identity under the selected-runtime fence. Reclamation SHALL report
completed, retained and deferred resources independently from activation.

#### Scenario: A consumer appears after initial observation

- **WHEN** a process, config or interpreter binding begins referencing a candidate before its deletion boundary
- **THEN** the fresh observation retains that generation
- **AND** selected and retained generation bytes remain unchanged.

#### Scenario: Historical observations accumulate

- **WHEN** repeated successful activations record paths of superseded runtimes
- **THEN** those historical records alone do not retain the runtimes
- **AND** reclamation neither deletes nor rewrites the historical records
- **AND** repeated cleanup converges without adding generation directories.

#### Scenario: Cleanup observation becomes unavailable

- **WHEN** runtime activation succeeds but a required consumer observation cannot be read
- **THEN** activation remains observable as successful and reclamation is deferred
- **AND** candidates without a completed fresh admission remain untouched
- **AND** the result reports the exact unavailable boundary and a public recovery action.

#### Scenario: A later cleanup step fails

- **WHEN** one generation is removed and a later observation or deletion fails
- **THEN** the report preserves the completed removal and identifies remaining paths
- **AND** retry derives fresh candidates rather than claiming rollback or repeating a vanished effect.

#### Scenario: Selector or candidate identity changes

- **WHEN** the selected runtime or exact candidate directory changes before its destructive effect
- **THEN** reclamation rejects the stale coordinate
- **AND** it does not delete a replacement directory under the old name.
