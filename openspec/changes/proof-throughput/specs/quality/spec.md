## ADDED Requirements

### Requirement: Complete verification throughput preserves assurance

ETHOS SHALL first target complete proof below 1,200 seconds on the declared
reference workstation at a measured, qualified worker count. The measurement SHALL include preparation,
all selected gates and cleanup, retaining at least 95-percent combined Python
line and branch coverage and every existing behavioral acceptance obligation.

#### Scenario: Complete performance acceptance

- **WHEN** an optimized exact-source full proof is measured
- **THEN** its elapsed time is below 1,200 seconds
- **AND** all required gates pass without narrower acceptance or hidden prework
- **AND** cold-computation and warm measurements are identified separately

#### Scenario: More workers improve verified throughput

- **WHEN** identical inputs at a higher worker count preserve results and isolation
- **THEN** ETHOS may adopt the faster count and qualify the complete proof there
- **AND** the two-worker baseline remains a comparison, not an execution ceiling
- **AND** process-loss recovery remains a separately tested obligation

#### Scenario: Subsequent throughput improvement

- **WHEN** the initial complete-proof target is reached
- **THEN** ETHOS evaluates the 600-second direction using measured remaining work
- **AND** neither infeasibility nor completion is inferred from local speedups

### Requirement: Verification preparation preserves its measured subject

ETHOS SHALL validate declared carrier ownership before executing tests that
consume it. Test preparation SHALL preserve the executing module's source
identity so coverage remains attributable regardless of worker assignment.

#### Scenario: A native adapter has no admitted carrier home

- **WHEN** the carrier gate rejects a candidate adapter's placement
- **THEN** the dependent test suite is not executed
- **AND** its result identifies the failed prerequisite without claiming execution

#### Scenario: Runtime supply variants share one test worker

- **WHEN** package and source supply fixtures run before runtime verification
- **THEN** the imported runtime module retains its original source identity
- **AND** subsequent executed verification remains observable to coverage

### Requirement: Native read batching preserves official semantics

ETHOS SHALL execute each bounded read batch through the selected official
OpenSpec package without copying its command parser or caching mutable results.
Every result SHALL bind its ordered input, native exit status and output.
Incomplete transport SHALL preserve failure evidence without claiming execution.

#### Scenario: An official command exits before the batch ends

- **WHEN** the native program exits during one read
- **THEN** completed frames preserve their native output and exit status
- **AND** unexecuted commands return an explicit interrupted result
- **AND** no effect command is admitted to the read batch

#### Scenario: Intent changes between public observations

- **WHEN** a later public plan observes changed OpenSpec inputs
- **THEN** it invokes the current official reader again
- **AND** an earlier successful observation cannot hide invalid current intent

### Requirement: Observation reuse preserves freshness and result identity

ETHOS SHALL reduce redundant computation using exact inputs and explicit
observation boundaries. Reuse SHALL preserve corruption detection and fresh
effect admission. Clearing derived caches SHALL change computation cost only,
not the verdict or selected effect.

#### Scenario: Relevant input changes

- **WHEN** source, rules, runtime, trust or coordinated state relevant to a
  decision changes
- **THEN** a prior cached result grants no current authorization
- **AND** only still-applicable immutable computation may be reused

#### Scenario: Complete source identity

- **WHEN** source includes staged, unstaged, untracked, deleted or executable-mode
  changes, including paths with index optimization flags
- **THEN** optimized observation preserves the native effective tree
- **AND** the caller's index and unrelated resources remain unchanged

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

#### Scenario: A test supervisor is killed

- **WHEN** a worker exits without executing its cleanup
- **THEN** a passing direct-command timeout test does not prove worker recovery
- **AND** native supervisor-loss and platform acceptance remain required

### Requirement: Native metadata comparisons preserve observation semantics

ETHOS SHALL compare mutable file metadata before and after reading through the
same native observation channel. Path and open-handle observations SHALL refer
to the same file identity, without equating platform-specific timestamp meanings.
Unsafe kinds and replaced files SHALL remain rejected without leaking handles.

#### Scenario: Stable Windows path and handle timestamps differ

- **WHEN** path stat and descriptor stat expose different stable ctime meanings
- **THEN** unchanged native merge metadata remains readable
- **AND** changes within either channel or replacement of the named file are rejected
- **AND** read-induced access-time changes do not masquerade as content mutation
