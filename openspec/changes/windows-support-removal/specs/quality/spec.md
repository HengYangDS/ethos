## ADDED Requirements

### Requirement: A read compares file metadata within one observation channel

ETHOS SHALL compare mutable file metadata before and after a read within one native observation
channel: the named path with the named path, and the open handle with the open handle. Both channels
SHALL refer to one file identity. Unsafe kinds and replaced files SHALL remain rejected without
leaking handles.

#### Scenario: A file changes or is replaced during the read

- **WHEN** the named file is replaced, or its metadata changes within either channel, between the
  first and the last observation of one read
- **THEN** the read is rejected
- **AND** no descriptor of the read stays open

#### Scenario: Only the access time moves

- **WHEN** a read changes nothing of the file but its access time, or the two channels report
  different change times for the unchanged file
- **THEN** the content is returned

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

#### Scenario: A command times out while a descendant holds its output

- **WHEN** a command times out while a descendant it started keeps its output open
- **THEN** the command ends and its caller returns within the cleanup bound
- **AND** the output the command wrote before it ended remains available

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

### Requirement: Locked execution keeps native mise policy

The environment that ETHOS gives an admitted repository command SHALL expose the locked tools with
configuration isolation, locked and offline selection, no automatic installation and no prompts. It
SHALL NOT carry resolution's safe mode, disposable state or trust, and a caller's explicit safe mode
and state directory SHALL apply. Trust SHALL remain mise's decision: ETHOS SHALL NOT trust a
configuration, edit a trust record or override a native refusal.

#### Scenario: An admitted command runs repository tasks

- **WHEN** an admitted command runs a repository task that runs another task through native mise
- **THEN** both tasks run with the locked tools

#### Scenario: The caller selected safe mode

- **WHEN** the caller's environment selects mise's safe mode
- **THEN** native mise still refuses to run repository tasks

#### Scenario: An untrusted configuration needs trust

- **WHEN** an admitted command reads an untrusted repository configuration that needs trust through
  a mise command that does not trust it
- **THEN** nothing in that configuration runs and ETHOS records no trust for it

#### Scenario: An admitted command runs a host command

- **WHEN** an admitted command runs a host command such as `git` or `tar`
- **THEN** its PATH holds the locked tools ahead of the host's own command baseline, and nothing
  else from the caller's PATH

#### Scenario: A mise configuration lies above the repository

- **WHEN** an operator's mise configuration lies in a directory above the repository, such as the
  home directory
- **THEN** native mise run by an admitted command from the repository reads only the repository's
  configuration, as resolution did
- **AND** the operator's tools, environment and tasks do not reach the command

### Requirement: The per-test bound detects hangs

The Python test gate SHALL bound each test by one declared hang limit, set well above the slowest
healthy test's duration inside a full proof at the admitted host load. A test MAY declare a shorter
limit to time one specific operation. No test SHALL declare a limit at or above the declared one.
Every thread's stack SHALL reach the run's log before the limit ends a test's process.

#### Scenario: A heavy test runs inside a busy full proof

- **WHEN** a test that takes 51 s alone takes 123 s inside a full proof at the admitted host load
- **THEN** its own assertions decide its result, not the hang limit

#### Scenario: A test stops making progress

- **WHEN** a test makes no progress
- **THEN** it fails at the declared limit and reports its stack

#### Scenario: A test raises its own limit

- **WHEN** a test declares a limit at or above the declared one, or a limit that is not a literal
- **THEN** the architecture regression fails

#### Scenario: A worker makes no progress

- **WHEN** a test makes no progress inside a pytest-xdist worker whose process the limit ends
- **THEN** every thread's stack is in the job log before the worker ends

### Requirement: Hosted host conformance runs in declared tiers

Hosted CI SHALL run host conformance in tiers. A push or pull request SHALL run Linux x64 at every
supported Python version and one macOS arm64 leg at the lowest. The full matrix, every supported
platform at every version, SHALL run only for a batch-head dispatch that names the head it qualifies
and for a drift schedule. A dispatch whose named head differs from its commit SHALL fail.

#### Scenario: A push runs the push tier

- **WHEN** `dev` or a proposal ref is pushed to GitHub
- **THEN** host conformance runs on Linux x64 at each supported Python version and on macOS arm64 at
  the lowest
- **AND** no other host conformance leg runs

#### Scenario: A batch head is qualified on GitHub

- **WHEN** a dispatch names the head it qualifies and runs at that commit
- **THEN** host conformance runs on every supported platform at every supported Python version

#### Scenario: A dispatch names a stale head

- **WHEN** a dispatch names a head that differs from the commit it runs at
- **THEN** no commit-scoped job runs
- **AND** the aggregate check fails

### Requirement: One aggregate check reports the per-push jobs

GitHub's projection SHALL carry one aggregate job, `hosted checks`, that needs every required job of
a commit run, commit-range admission and the required suite legs included, and runs whatever their
results. It SHALL pass only when each needed job succeeded where its event runs it and was skipped
only where its event has no such job. It SHALL NOT need a job that may fail: the external link
observation. Its result is a host observation, not repository proof.

#### Scenario: A per-push job fails

- **WHEN** commit-range admission, a host conformance leg or the quality gates job fails or is
  cancelled
- **THEN** `hosted checks` fails

#### Scenario: A job is skipped on a commit run

- **WHEN** a push of `dev` or a proposal ref, or a pull request, ends with commit-range admission,
  host conformance or the quality gates job skipped
- **THEN** `hosted checks` fails

#### Scenario: An event has no such job

- **WHEN** `main` follows `dev` and its admission succeeds, or a batch-head dispatch or the drift
  schedule ends with every commit-scoped job successful
- **THEN** `hosted checks` succeeds with the jobs that the event does not have skipped

#### Scenario: A push has no suite leg

- **WHEN** a push or a pull request ends with its per-push jobs successful and the suite legs
  skipped
- **THEN** `hosted checks` succeeds

#### Scenario: A required suite leg fails

- **WHEN** a batch-head dispatch or the drift schedule ends with the Linux x64 leg at Python 3.12 or
  at 3.13 failed, cancelled or skipped
- **THEN** `hosted checks` fails

#### Scenario: The external link observation fails

- **WHEN** external link health finds an unreachable or redirecting link while every required
  per-push job succeeds
- **THEN** its job keeps its report and fails by its declared tolerance without failing the run
- **AND** `hosted checks`, which neither needs that job nor reads its result, succeeds

### Requirement: Suite legs repeat the test suite once for a release

A batch-head dispatch and the drift schedule SHALL repeat the Python test suite, through the shipped
behavior probe and within the test gate's deadline, on Linux x64 at Python 3.12 and 3.13. With the
quality gates job on Linux arm64 and the local proof on macOS arm64, each operating system, both
architectures and each supported Python version then run the suite once for a release. Every suite
leg SHALL be required.

#### Scenario: A batch head is qualified

- **WHEN** a dispatch names the head it qualifies and runs at that commit
- **THEN** the suite runs on Linux x64 at Python 3.12 and at 3.13
- **AND** each leg runs the tests on the interpreter of its own Python version
- **AND** each leg uploads its JUnit and coverage reports whether its tests pass or fail

#### Scenario: A push or pull request runs no suite leg

- **WHEN** `dev` or a proposal ref is pushed, or a pull request is opened or updated
- **THEN** no suite leg runs

#### Scenario: The test gate's deadline bounds a leg

- **WHEN** a suite leg is projected
- **THEN** it passes the timeout that the test gate declares to the probe as the suite's deadline
- **AND** the leg's environment sync and its suite share that one deadline
- **AND** a suite job class whose timeout does not exceed that timeout by the declared margin for
  the leg's supply steps does not compile

### Requirement: Native adoption preserves declared byte identity

Adoption SHALL bind its write plan to exact UTF-8 bytes independently of host newline translation.
Retained authored bindings SHALL preserve their original bytes and matching digest. New writes and
compensation SHALL share the existing atomic writer, without claiming multi-file crash atomicity.

#### Scenario: New bindings carry their declared bytes

- **WHEN** an admitted adoption writes new bindings
- **THEN** actual file digests equal the declared write-plan digests
- **AND** CLI, SDK and MCP retain the same exact-byte acceptance

#### Scenario: Authored bindings use a different newline convention

- **WHEN** valid existing bindings contain LF, CRLF or CR bytes
- **THEN** adoption keeps those bytes and reports their exact digests
- **AND** a later binding-write failure restores any earlier empty binding or removes its new file

## REMOVED Requirements

### Requirement: Generated Windows verification jobs retry their source checkout

**Reason**: The common CI model declares no Windows runner system (owner's decision of 2026-11-25),
so it generates no Windows verification job.

**Migration**: A governed repository removes its Windows runner declarations; a declaration that
names the system `windows` no longer compiles. Successors: `none`.

### Requirement: Native metadata comparisons preserve observation semantics

**Reason**: Its only scenario described a Windows difference between the change times that a path
and an open handle report, and ETHOS supports no Windows host (owner's decision of 2026-11-25).

**Migration**: None for an adopter: the comparison is unchanged. The requirement "A read compares
file metadata within one observation channel" states it without naming a platform.
