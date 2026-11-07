## MODIFIED Requirements

### Requirement: Owned temporary resources converge after owner loss

Test, package and runtime scratch SHALL have an exact producer, consumer and
retention boundary. Normal finalization and bounded dead-owner recovery SHALL
reclaim only proved-owned, unreferenced bytes; missing liveness or ownership
SHALL remain UNKNOWN rather than authorize deletion.

#### Scenario: Repeated process death does not accumulate scratch

- **WHEN** normal, exceptional and killed invocations repeat with fixed inputs and concurrency
- **THEN** successor and idle maintenance bound dead-root count, bytes, inodes and reclamation delay
- **AND** live workers, shared uv supply and caller-owned basetemp survive
- **AND** contention, PID reuse, path replacement, links and read-only inodes cannot cause unsafe cleanup

#### Scenario: Long-running resource acceptance is independently observed

- **WHEN** source-bound real workloads are observed across 24- and 48-hour windows
- **THEN** growth, orphan age, high-water usage, cleanup latency and indexing cost remain within declared limits
- **AND** a short green test or one manual sweep does not satisfy this observation

#### Scenario: A host cleaner that removes files by access age spares a running attempt

- **WHEN** the host removes temporary files that were not accessed for days, and the behavior
  probe's environment was installed from a cache with old times
- **THEN** before its tests run, every file and directory of that environment carries an access
  time from the attempt and its own modification time
- **AND** the renewal never follows a symlink out of the scratch
- **AND** a scan mirror or fixture copy carries fresh times, never its source's
