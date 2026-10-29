## MODIFIED Requirements

### Requirement: Singular Quality Entry

`ethos prove` SHALL be the only public quality selection and execution surface.
Cyclopts operation declarations own CLI syntax; gate IDs own proof selection.

#### Scenario: A focused check is requested

- **WHEN** a caller runs `ethos prove --gate <gate-id> --json`
- **THEN** ETHOS plans the exact gate and dependency closure
- **AND** `--execute` runs that plan and returns evidence
- **AND** no `ethos quality` command group, generic report-handler DSL, command
  registry, wrapper alias, or re-export facade exists

#### Scenario: A focused check verifies no code property

- **WHEN** a caller runs `ethos prove --gate <gate-id>` and no selected gate verifies a
  code-correctness axis or declares a quality dimension
- **THEN** the selection compiles no code-correctness obligation, whether the gate's implementation
  lives in the repository's tree or in the judging product
- **AND** the source contracts whose members the selected gates read remain selected
- **AND** the focused result still cannot satisfy promotion without the complete required floor

### Requirement: Interrupted commands retain effect and process ownership boundaries

A synchronous command interrupted while its caller remains alive SHALL stop its
owned descendants before reporting completed cleanup. The original failure and
available output SHALL remain observable. Process-group control SHALL identify
its platform and containment limits; it SHALL NOT imply recovery after loss of
the supervisor or containment of deliberately detached processes.

#### Scenario: POSIX command timeout or caller cancellation

- **WHEN** a running command has a ready descendant in its owned process group
- **AND** its caller observes a timeout or cancellation
- **THEN** the group is terminated without signalling the caller's group
- **AND** inherited output pipes do not leave the descendant running
- **AND** the original exception and captured timeout output remain available

#### Scenario: Native executable verification times out

- **WHEN** a version-check executable has a ready descendant and exceeds its deadline
- **THEN** the shared process owner closes its process group before returning failure
- **AND** the verified archive and previous executable retain their existing protections
- **AND** transport and verification do not define competing cancellation semantics

#### Scenario: A parallel proof caller is interrupted

- **WHEN** the proof caller is interrupted while worker threads own native commands
- **THEN** the shared process owner cancels those groups before the executor joins its workers
- **AND** late command creation is denied within the cancelled invocation
- **AND** the original interruption remains observable without a passing proof claim
- **AND** an independent subsequent invocation has fresh command ownership

#### Scenario: A test supervisor is killed

- **WHEN** a worker exits without executing its cleanup
- **THEN** a passing direct-command timeout test does not prove worker recovery
- **AND** native supervisor-loss and platform acceptance remain required

#### Scenario: A provider reports a failure from a nested scope

- **WHEN** a gate provider's nested command scope fails and the provider reports that failure as its
  result
- **THEN** the failure cancels only the commands started under that nested scope
- **AND** sibling gates and the enclosing proof keep creating and completing their own commands
- **AND** cancelling the enclosing proof still ends every command of its nested scopes

### Requirement: Native tool supply has one declaration and bounded bootstrap

Development and CI SHALL consume the same mise tool selections and platform
locks. Ecosystem dependency locks SHALL remain with their package managers.
Observation SHALL NOT install tools. Provisioning SHALL preserve current
executables on failure, retain native diagnostics, and remove owned scratch.

#### Scenario: A clean runner has no mise installation

- **WHEN** the existing bootstrap executes with no prepared native mise
- **THEN** the version-bound official installer runs in owned staged storage with a deadline
- **AND** only a successfully verified executable is published
- **AND** preparation of locked gate tools completes before gate execution
- **AND** every same-invocation consumer uses that exact prepared executable without rediscovering PATH or an obsolete cache directory

#### Scenario: Operator-managed mise is newer than the declared minimum

- **WHEN** an existing stable operator executable meets the native minimum version
- **THEN** preparation reuses it without installing or replacing another executable
- **AND** staged bootstrap supply still requires its exact declared version
- **AND** older, prerelease, malformed or warning-bearing observations cannot pass

#### Scenario: Native Windows observation inherits another PowerShell's modules

- **WHEN** ACL or process observation starts native Windows PowerShell through an intermediate process
- **THEN** its child environment excludes the inherited module search path
- **AND** the parent environment, native error and timeout boundaries remain intact

#### Scenario: Native preparation fails or is interrupted

- **WHEN** download, archive validation, executable validation or execution times out or fails
- **THEN** the previous executable remains unchanged and owned descendants are drained
- **AND** unapproved version diagnostics prevent publication
- **AND** verified cache reuse preserves identity without repeating downloads

#### Scenario: A shared check resolves a declared tool on a clean runner

- **WHEN** a shared quality check resolves a tool that the repository's mise configuration declares,
  such as Node for the static JavaScript floor, on a clean CI runner
- **THEN** CI preparation has installed that tool through mise from the locked selection that
  development uses
- **AND** an immutable supply image that lacks the tool fails preparation before any gate runs and
  names the tool
