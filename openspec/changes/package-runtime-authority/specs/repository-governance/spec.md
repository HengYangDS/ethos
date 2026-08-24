## MODIFIED Requirements

### Requirement: Hook runtime currentness is mutation admission
ETHOS SHALL distinguish runtime byte integrity from accepted-source currentness.
A hook runtime SHALL authorize repository mutation only when it is the single
Git-common-dir selected runtime, its manifest is valid, and its source commit
and tree equal the exact expected ETHOS identity.

#### Scenario: intact runtime was built from older accepted source
- **WHEN** every recorded runtime byte is intact but its source commit or tree differs from the expected accepted identity
- **THEN** runtime observation reports a stable stale-source required gap
- **AND** prewrite, hook, ref effect, and lifecycle mutation paths fail closed

#### Scenario: accepted runtime is current
- **WHEN** the selected runtime bytes, launchers, source commit, and source tree all match their expected identities
- **THEN** the existing hook runtime binding reports no required gap
- **AND** hooks, diagnosis, repair, and package-only commands resolve that same selected immutable runtime.

#### Scenario: repair replaces the stale projection
- **WHEN** the exact public repair command succeeds
- **THEN** the command validates the candidate runtime and complete hook bundle before atomically selecting it
- **AND** post-observation proves selection, byte integrity, source currentness, and launcher binding before reporting success.

#### Scenario: proof is missing at hook admission
- **WHEN** a hook denies an exact HEAD because its required proof is absent
- **THEN** the report contains one executable command bound to the selected runtime, repository root, and exact HEAD
- **AND** the command does not depend on ambient `PATH` command discovery.

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
- **THEN** it retains the selected runtime and every generation named by effective config, live process commands, or in-flight operation records
- **AND** it removes only other generated runtimes and hook generations
- **AND** an unreadable consumer source blocks deletion.

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
