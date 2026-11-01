## ADDED Requirements

### Requirement: ETHOS proves its Python suite through the probe it ships

ETHOS SHALL run its Python test suite in proof only through the Python behavior probe it ships to
governed repositories, declared as a provider row of its gate registry. No gate command, Nox session
or repository script SHALL start another pytest session for a default or full proof, so a defect in
the shipped probe fails ETHOS's own proof.

#### Scenario: The proof sets resolve one Python test runner

- **WHEN** ETHOS's default or full proof set is resolved
- **THEN** exactly one selected gate runs ETHOS's Python tests, through the shipped behavior probe
  provider
- **AND** no selected gate command, and no Nox session such a command starts, launches pytest

#### Scenario: A second runner is introduced

- **WHEN** a change adds a gate command, Nox session or repository script that starts pytest for a
  proof
- **THEN** the single-runner regression fails

#### Scenario: The shipped probe regresses

- **WHEN** a change breaks how the shipped probe runs or judges a repository's tests
- **THEN** ETHOS's own proof of that change fails at its Python test gate

### Requirement: The behavior probe runs under the repository's native test configuration

The Python behavior probe SHALL run pytest with the repository's paradigm pytest carrier and the
repository root as rootdir, and SHALL measure coverage with its paradigm coverage carrier, when the
repository declares them. It SHALL bound the run by the gate's declared timeout, otherwise 600
seconds. A repository without these carriers keeps pytest's native discovery and coverage of the
whole tree.

#### Scenario: The paradigm carriers are declared

- **WHEN** a repository declares `.config/checks/pytest/pytest.toml` and
  `.config/checks/coverage/coverage.toml`
- **THEN** pytest collects and reports as the pytest carrier declares, with node identities relative
  to the repository root
- **AND** coverage uses the coverage carrier's source, branch, subprocess and floor settings, so a
  declared floor that is not met blocks the behavior evidence

#### Scenario: No carrier is declared

- **WHEN** a repository declares neither carrier
- **THEN** pytest discovers its own configuration and coverage measures the repository tree, as
  before

#### Scenario: A gate declares a longer timeout

- **WHEN** the gate that runs the probe declares `timeout_seconds` above 600
- **THEN** that value bounds the pytest run
- **AND** a gate that declares none keeps the 600-second bound

### Requirement: Probe reports belong to one attempt

The behavior probe SHALL write the JUnit report, the pytest report log and the Cobertura report of
one attempt into that attempt's report root, and SHALL name the root to the test process for further
native results. When the runner names a native output root, the probe SHALL copy the attempt's
reports there. Bytecode and Hypothesis storage that its test processes write SHALL stay in the
attempt's scratch, which the probe SHALL remove through the shared owned-removal owner.

#### Scenario: The runner names a native output root

- **WHEN** `ETHOS_NATIVE_OUTPUT_DIR` names a directory for the proof
- **THEN** that directory receives exactly this attempt's JUnit report, report log, Cobertura report
  and the results the suite wrote into the attempt's report root
- **AND** the behavior verdict is decided from the attempt's own reports, not from the copy

#### Scenario: No native output root is named

- **WHEN** the runner names no native output root
- **THEN** nothing the attempt produced remains outside its scratch after the probe returns

#### Scenario: The test process writes bytecode

- **WHEN** the test process, or a child that keeps its environment, compiles a module
- **THEN** the bytecode lands under the attempt's scratch and is removed with it
- **AND** no `__pycache__` directory appears beside the repository's sources

#### Scenario: The test process writes Hypothesis storage

- **WHEN** a test writes under the directory Hypothesis's `HYPOTHESIS_STORAGE_DIRECTORY` names
- **THEN** the writes land under the attempt's scratch and are removed with it
- **AND** the repository's worktree gains no tracked, untracked or ignored path

#### Scenario: A test leaves a linked or sealed path in its scratch

- **WHEN** the attempt's scratch contains a link to an external file or an owner-inaccessible
  directory
- **THEN** removal keeps the external file's bytes, mode and modification time and changes only the
  directory permissions that removal requires

### Requirement: ETHOS reports what each test case crosses

ETHOS's test run SHALL record, for each case whose setup, call or teardown opens, lists, removes or
renames a file, starts a process, opens a database or connects a socket, which of these it crossed
and whether that exceeds the tier its directory states. Recording SHALL NOT change a case's outcome.
Module loading, the test tools' own work, the run's own report root and the setup of fixtures wider
than function scope SHALL NOT count as crossings.

#### Scenario: A unit case reads a file

- **WHEN** a case under `tests/unit` opens a file during its call
- **THEN** its JUnit test case and report-log entry record the `open` crossing and mark it as
  exceeding its tier
- **AND** the case keeps the outcome its assertions decide

#### Scenario: A case imports a module during its call

- **WHEN** a case's call imports a module that was not yet loaded
- **THEN** the import machinery's file reads and directory listings are not recorded

#### Scenario: A case's fixture crosses

- **WHEN** a function-scoped fixture of a case writes a file during its setup or its teardown
- **THEN** the crossing is recorded for that case

#### Scenario: A test tool or a shared fixture crosses

- **WHEN** Hypothesis or pytest reads or writes files for their own work, or a session-scoped
  fixture is set up, while a case runs
- **THEN** no crossing is recorded for that case

#### Scenario: A case outside `tests/unit` connects

- **WHEN** such a case connects a socket to an address other than loopback
- **THEN** the crossing is recorded and marked as exceeding its tier
- **AND** a loopback connection by the same case is recorded without exceeding it

## MODIFIED Requirements

### Requirement: Capability-Preserving Test Floor

The Python test owner SHALL run bounded parallel tests, warnings as errors, branch coverage,
architecture tests, property tests, and declared concurrency or CAS tests. Coverage policy SHALL
come only from the repository's native coverage configuration,
`.config/checks/coverage/coverage.toml`. The required combined line-and-branch coverage SHALL be at
least 95 percent across the declared Python product. Measurement SHALL NOT redefine the requirement
as an aspiration.

#### Scenario: Change proof executes the complete test surface

- **WHEN** the unit-architecture gate completes
- **THEN** it runs the complete declared test surface with warnings as errors and emits
  branch-coverage evidence bound to the exact HEAD
- **AND** the same execution decides the coverage floor, so default proof, full proof, and local CI
  neither rerun the tests nor read coverage evidence from another attempt
- **AND** coverage below the required floor blocks acceptance rather than being excused as existing
  debt or changing the floor
- **AND** authority, CAS, and reducer owners may declare stricter local floors
- **AND** a test that only reaches a branch without asserting behavior is not a substitute for
  capability proof

#### Scenario: A coverage regression exposes unsafe compensation

- **WHEN** an archive result names the repository root, another Change, a non-archive path, or a
  symlink alias
- **THEN** the receipt supplies no deletion authority for that path
- **AND** the Git effect owner refuses root, traversal, linked, and tracked removal targets even
  when called independently of the archive adapter
- **AND** a failed command with an exactly bound archive path may still be compensated through the
  same owner
- **AND** remaining unowned content is preserved and reported as retained residue; a restored index
  alone does not prove compensation complete

#### Scenario: A coverage regression exposes incomplete runtime-consumer observation

- **WHEN** a current consumer root is not a readable real directory, or a nested entry is linked,
  unreadable, neither a directory nor a regular file, or cannot be completely enumerated
- **THEN** the existing activation observer reports unknown consumers and blocks generation
  retirement instead of treating an incomplete scan as no references
- **AND** a dangling root link is not a genuinely absent consumer directory
- **AND** initial observation failure preserves the selector, Lease state, and runtime generations
- **AND** readable nested receipts retain their referenced generations through the same observer for
  operations, transactions, and ref intents

#### Scenario: A coverage regression exposes destructive start compensation

- **WHEN** Work Lane start fails after recognizing existing resources or while creating new
  resources
- **THEN** compensation applies only to proved creations of that invocation, preserving reused
  worktrees, their contents, refs, and Lease rows
- **AND** a missing worktree effect receipt cannot authorize deletion of a path that appeared during
  the operation
- **AND** new worktree cleanup does not force removal of later user content; failed or unknown
  removal retains the supporting ref and Lease
- **AND** only a newly acquired exact four-field Lease can be revoked through the existing
  revocation owner; expiry drift blocks removal and preserves the ref
- **AND** cleanup failure remains visible rather than becoming a clean rollback

#### Scenario: Accepted runtime expectation observes immutable source objects

- **WHEN** the accepted checkout contains untracked observations or staged source/version edits, or
  the canonical checkout is detached
- **THEN** runtime expectation compiles the configured accepted ref's exact commit, tree, and
  canonical version blob without modifying checkout contents
- **AND** accepted-ref advancement changes the expected identity, while invalid accepted version
  bytes fail closed
- **AND** constructing a runtime still requires the wheel's complete build identity to equal that
  accepted expectation; mutable source cannot be silently labeled as accepted

#### Scenario: Coverage exposes obsolete coordination projection semantics

- **WHEN** current peer scopes and candidate progress are observed with valid four-field Leases
- **THEN** the collaboration projection reports those facts without inventing queue membership,
  queue age, or mutation-admission order from Lease data
- **AND** unknown or deferred scope takes precedence over overlap; overlap requires coordination and
  disjoint scopes remain independent
- **AND** candidate lag takes precedence over a stale progress interval; neither advisory condition
  mints mutation authority

#### Scenario: Design-integrity failure remains diagnosable

- **WHEN** a tracked canonical design owner, required projection, or root axiom document is missing
- **THEN** the existing design-integrity audit returns its exact blocking missing-document finding
  rather than throwing during an auxiliary check
- **AND** derivation comparison uses the same observed document set; an untracked document cannot
  silently become the canonical owner
- **AND** the root README and engineering axioms preserve the canonical distinction between
  transient Commitment and durable Attestation, rather than reviving the retired
  persistent-Commitment model

#### Scenario: Hosted proof crosses an identity boundary

- **WHEN** a hosted provider supplies a locked test environment and executes the complete test
  surface under a less privileged identity
- **THEN** all declared native executables are available before the proof starts
- **AND** run-as control inputs are consumed exactly once at the privilege boundary and are absent
  from the descended test environment
- **AND** the complete lock-bound Node package tree is resolved once at the repository session
  boundary and inherited by OpenSpec, package construction, nested tests, and Node-backed quality
  tools through one absolute coordinate
- **AND** repository-owned caches and other tool entrypoints inherited by nested processes use
  absolute, locked coordinates
- **AND** no nested test or build falls back to an ambient executable, cache, or network resolution
- **AND** the resulting evidence remains attributable to that hosted provider and exact HEAD

#### Scenario: A parallel test worker is lost

- **WHEN** a pytest worker crashes or a thread timeout terminates it during the current proof
- **THEN** the Python test gate records one terminal failure for that proof
- **AND** xdist does not restart a worker or replay the lost test in the same proof attempt
- **AND** the failure identifies the lost worker and test
- **AND** the gate does not increase timeout, retry the test, or weaken the required test surface.

#### Scenario: The configured floor is weakened

- **WHEN** a policy change would admit a measurement below 95 percent
- **THEN** the executed boundary regression fails independently of the changed declaration
- **AND** restoring the required floor rejects a 94 percent measurement and accepts a 95 percent
  measurement when all other evidence preconditions hold
- **AND** excluded product paths, disabled branches, suppressed lines, or tests without behavior
  assertions are not valid ways to satisfy the requirement

### Requirement: Hosted verification preserves its evidence plane

Hosted CI SHALL execute declared source-quality owners against the exact event object without
requiring a local Work Lane, Lease, candidate checkout, active Change, or installed mutation hooks.
Its result SHALL remain host observation, not repository acceptance proof, and SHALL retain gate and
command failure facts. Local proof, native package conformance, and provider success remain
independent obligations.

#### Scenario: Hosted checkout has no local lifecycle state

- **WHEN** hosted verification runs at the expected object
- **THEN** the declared default gate set, including the Python test gate and the coverage floor its
  execution decides, executes with its dependency closure through the existing gate owner
- **AND** official OpenSpec validation runs from the locked repository supply
- **AND** absent local candidate/runtime state does not authorize mutation or invalidate a passing
  host observation

#### Scenario: Result is stale, malformed, empty, or unsuccessful

- **WHEN** execution fails, HEAD changes, coordinates disagree, required gaps remain, or the
  observation envelope is invalid
- **THEN** the hosted receipt blocks and preserves the available diagnostics
- **AND** no passing local status or unrelated proof can override that result

#### Scenario: Locked runtime export has no ambient Python

- **WHEN** a package runtime invokes uv with its authenticated interpreter in an offline minimal
  environment
- **THEN** uv selects that exact interpreter without a download or ambient rediscovery
- **AND** lock, dependency, and runtime identity checks remain enforced

### Requirement: Quality Execution Closure

The declared quality graph SHALL select and execute each required obligation once for the requested
evidence plane. Local CI and repository proof SHALL reuse the same gate identities, dependency
closure and shared runner rather than maintain independent membership or scheduling state. Offline
source correctness, online freshness, package verification and hosted observation SHALL remain
distinguishable; an unobserved external property SHALL NOT be reported as a passing local property.

#### Scenario: The same quality plane is invoked from two entrypoints

- **WHEN** local CI and repository proof evaluate the same source and requested quality plane
- **THEN** their required gate identities and dependency closure agree
- **AND** each required check executes at most once through its existing owner
- **AND** the result identifies checks outside that evidence plane without silently dropping
  obligations or claiming hosted success

#### Scenario: A prerequisite did not pass

- **WHEN** execution is requested and a gate has a failed, unknown or unexecuted prerequisite
- **THEN** the shared runner does not execute that dependent gate
- **AND** its result is blocked and identifies the unmet prerequisite
- **AND** independent diagnostic checks may continue within the declared budget

#### Scenario: Coverage fails before package delivery

- **WHEN** the required Python test result, whose execution decides the coverage floor, is not
  passing
- **THEN** dependent package creation and installation do not execute
- **AND** no success receipt is emitted for the incomplete quality closure

#### Scenario: External observation is unavailable

- **WHEN** a requested online freshness or hosted-observation check cannot obtain its declared
  evidence
- **THEN** the result records unknown or blocked with an actionable cause
- **AND** offline source correctness is neither relabeled as external assurance nor made dependent
  on an undeclared remote

#### Scenario: Readiness is not executed proof

- **WHEN** the graph is projected without execution
- **THEN** all planned results remain unknown with no exit code
- **AND** unmet execution prerequisites are not reported as observed failures

#### Scenario: Fallback evidence must describe the tested source

- **WHEN** local CI is requested against uncommitted source or an invalid selection
- **THEN** it records a non-passing preflight result without executing the closure
- **AND** changes to HEAD, working bytes or policy during execution invalidate the result

#### Scenario: Execution evidence is incomplete or interrupted

- **WHEN** execution is interrupted or has missing, duplicate, mismatched or unsuccessful results
- **THEN** the fallback receipt cannot report success
- **AND** a non-passing record exists before execution and records incomplete observation

### Requirement: Independent test work is distributable

The Python test owner MAY distribute independent test items across parallel workers. Distribution
SHALL NOT change the selected tests, worker limits, isolation, coverage or outcomes, and the
distribution mode SHALL be the repository's native test configuration rather than a fixed mechanism.
Serial execution SHALL remain supported.

#### Scenario: One module contains the longest independent test scope

- **WHEN** multiple workers execute independent test items in that module
- **THEN** the scheduler can distribute its pending items across workers
- **AND** the collected test identities and required outcomes remain unchanged

#### Scenario: The native distribution mode changes

- **WHEN** the repository's pytest configuration selects another native distribution mode, or serial
  execution
- **THEN** the executed test identities, outcomes and coverage are those of the previous mode

## REMOVED Requirements

### Requirement: Test attempt completion is committed last

**Reason**: The evidence lock, completion marker and shard and partial-output handling belonged to
the retired `tools/ci` test gate, which wrote one shared evidence home that later attempts and a
separate coverage-floor gate read. The shipped probe runs each attempt in its own scratch root and
returns its verdict and reports from that attempt alone, and the same execution decides the coverage
floor, so no earlier completion, fragment or partial population can describe a later attempt.

**Migration**: Consumers read the attempt's own result: proof checks carry the probe's evidence, and
hosted verification receives that attempt's reports through the native output root. Owned cleanup
keeps its obligations under "Owned removal minimizes permission effects" and "Probe reports belong
to one attempt".
