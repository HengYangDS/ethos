## ADDED Requirements

### Requirement: Complete verification throughput preserves assurance

ETHOS SHALL target complete proof within 600 seconds on the declared reference
workstation with two workers. The measurement SHALL include command preparation,
all selected gates and cleanup, retaining at least 95-percent combined Python
line and branch coverage and every existing behavioral acceptance obligation.

#### Scenario: Complete performance acceptance

- **WHEN** an optimized exact-source full proof is measured
- **THEN** its elapsed time is at most 600 seconds
- **AND** all required gates pass without narrower acceptance or hidden prework
- **AND** cold-computation and warm measurements are identified separately

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
