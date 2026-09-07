## MODIFIED Requirements

### Requirement: Capability-Preserving Test Floor

The Python test owner SHALL run bounded parallel tests, warnings as errors,
branch coverage, architecture tests, property tests, and declared concurrency or
CAS tests. Coverage policy SHALL come only from
`.config/checks/coverage/policy.toml`. The required combined line-and-branch
coverage SHALL be at least 95 percent across the declared Python product.
Measurement SHALL NOT redefine the requirement as an aspiration.

#### Scenario: Change proof executes the complete test surface

- **WHEN** the unit-architecture gate completes
- **THEN** it runs the complete declared test surface with warnings as errors and
  emits branch-coverage evidence bound to the exact HEAD
- **AND** default proof, full proof, and local CI run the same dependent
  coverage-floor owner against that evidence without rerunning the tests
- **AND** coverage below the required floor blocks acceptance rather than being
  excused as existing debt or changing the floor
- **AND** authority, CAS, and reducer owners may declare stricter local floors
- **AND** a test that only reaches a branch without asserting behavior is not a
  substitute for capability proof

#### Scenario: Hosted proof crosses an identity boundary

- **WHEN** a hosted provider supplies a locked test environment and executes the
  complete test surface under a less privileged identity
- **THEN** all declared native executables are available before the proof starts
- **AND** run-as control inputs are consumed exactly once at the privilege
  boundary and are absent from the descended test environment
- **AND** the complete lock-bound Node package tree is resolved once at the
  repository session boundary and inherited by OpenSpec, package construction,
  nested tests, and Node-backed quality tools through one absolute coordinate
- **AND** repository-owned caches and other tool entrypoints inherited by
  nested processes use absolute, locked coordinates
- **AND** no nested test or build falls back to an ambient executable, cache, or
  network resolution
- **AND** the resulting evidence remains attributable to that hosted provider
  and exact HEAD

#### Scenario: A parallel test worker is lost

- **WHEN** a pytest worker crashes or a thread timeout terminates it during the
  current proof
- **THEN** the Python test gate records one terminal failure for that proof
- **AND** xdist does not restart a worker or replay the lost test in the same
  proof attempt
- **AND** the failure identifies the lost worker and test
- **AND** the gate does not increase timeout, retry the test, or weaken the
  required test surface.

#### Scenario: The configured floor is weakened

- **WHEN** a policy change would admit a measurement below 95 percent
- **THEN** the executed boundary regression fails independently of the changed
  declaration
- **AND** restoring the required floor rejects a 94 percent measurement and
  accepts a 95 percent measurement when all other evidence preconditions hold
- **AND** excluded product paths, disabled branches, suppressed lines, or tests
  without behavior assertions are not valid ways to satisfy the requirement

