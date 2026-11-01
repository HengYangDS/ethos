## ADDED Requirements

### Requirement: Host conformance runs its platform cases in one process

The host proof SHALL run its platform conformance cases in one pytest process, whatever worker count
the shared test configuration selects.

#### Scenario: The shared configuration selects workers

- **WHEN** the shared pytest configuration selects pytest-xdist workers for every run
- **THEN** the host proof's cases still run in one process, as when they were verified
