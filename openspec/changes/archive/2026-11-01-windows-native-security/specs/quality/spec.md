## MODIFIED Requirements

### Requirement: Interrupted commands retain effect and process ownership boundaries

A synchronous command interrupted while its caller remains alive SHALL stop its owned descendants
before reporting completed cleanup. The original failure and available output SHALL remain
observable. Process-group control SHALL identify its platform and containment limits; it SHALL NOT
imply recovery after loss of the supervisor or containment of deliberately detached processes.

#### Scenario: POSIX command timeout or caller cancellation

- **WHEN** a running command has a ready descendant in its owned process group
- **AND** its caller observes a timeout or cancellation
- **THEN** the group is terminated without signalling the caller's group
- **AND** inherited output pipes do not leave the descendant running
- **AND** the original exception and captured timeout output remain available

#### Scenario: Windows command timeout with a descendant holding its output

- **WHEN** a Windows command times out while a descendant it started keeps its output open
- **THEN** the command ends and its caller returns within the cleanup bound
- **AND** the output the command wrote before it ended remains available
- **AND** the descendant is outside containment, which the result does not report as stopped

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

Development and CI SHALL consume the same mise tool selections and platform locks. Ecosystem
dependency locks SHALL remain with their package managers. Observation SHALL NOT install tools.
Provisioning SHALL preserve current executables on failure, retain native diagnostics, and remove
owned scratch.

#### Scenario: A clean runner has no mise installation

- **WHEN** the existing bootstrap executes with no prepared native mise
- **THEN** the version-bound official installer runs in owned staged storage with a deadline
- **AND** only a successfully verified executable is published
- **AND** preparation of locked gate tools completes before gate execution
- **AND** every same-invocation consumer uses that exact prepared executable without rediscovering
  PATH or an obsolete cache directory

#### Scenario: Operator-managed mise is newer than the declared minimum

- **WHEN** an existing stable operator executable meets the native minimum version
- **THEN** preparation reuses it without installing or replacing another executable
- **AND** staged bootstrap supply still requires its exact declared version
- **AND** older, prerelease, malformed or warning-bearing observations cannot pass

#### Scenario: Native Windows observation inherits another PowerShell's modules

- **WHEN** ACL or process observation runs on Windows under an intermediate process that exports
  another PowerShell edition's module path
- **THEN** it starts no PowerShell child
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

### Requirement: Hosted supply preparation precedes expensive verification

Hosted verification SHALL prepare its declared scanner, budget and SBOM supply through the existing
supply owners before starting proof. Preparation failure SHALL preserve native diagnostics and exit
status, invalidate previous attempt reports, and produce a failed hosted observation without
executing proof. Package execution SHALL still validate supply in its own current environment.

#### Scenario: A declared tool cannot be prepared

- **WHEN** scanner, budget or SBOM preparation fails
- **THEN** expensive proof does not start and the native failure remains observable
- **AND** old proof, test and coverage reports cannot describe the new attempt
- **AND** the hosted receipt identifies failed supply without issuing an Attestation

#### Scenario: Prepared supply permits exact-source verification

- **WHEN** every required preparation succeeds
- **THEN** verification executes against the requested exact source
- **AND** a retained adopter runtime selector cannot redirect source CI to older code
- **AND** the later package boundary retains its own executable validation

#### Scenario: Linux runner reuses locked immutable supply

- **WHEN** a new GitLab checkout begins on a cold ARM64 runner
- **THEN** its image is selected by published OCI digest, not a mutable tag or local cache hit
- **AND** the image's input hashes match the checkout's Python and Node locks before provisioning or
  proof
- **AND** APT, PyPI and npm registry access are not required by the quality job
- **AND** missing or mismatched supply fails before any quality result is issued

#### Scenario: A Change alters a supply input

- **WHEN** a lane changes a file that the supply image's input manifest hashes, such as `uv.lock`
- **THEN** the lane binds an image built from its own proposal commit before it lands
- **AND** GitLab verifies the landed head with that image instead of refusing it

#### Scenario: One selected Forge remains executable without its peer

- **GIVEN** two selected Forges project the same exact source and required CI graph
- **WHEN** one Forge's registry and release endpoints are unavailable and the other's runner has no
  local image or tool cache
- **THEN** the available Forge executes every required job from its own verified supply or
  independent sources
- **AND** the selected source, supply materials and resulting evidence remain bound to that Forge's
  run
- **AND** missing bytes or a peer-dependent fetch blocks before proof rather than accepting a
  warm-cache or other-Forge result

#### Scenario: Unqualified image is not published

- **WHEN** a newly built image cannot bootstrap a fresh checkout without network access
- **THEN** the build job fails before pushing that image
- **AND** the previously published digest remains available for diagnosis or rollback

#### Scenario: Native provisioning exceeds its execution deadline

- **WHEN** a native tool emits partial output before its bounded preparation times out
- **THEN** the supply entrypoint reports both available streams and the exact failed command
- **AND** owned descendants terminate before preparation scratch is removed
- **AND** a preceding successful tool cannot be mistaken for the failed attempt
