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
