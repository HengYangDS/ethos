## ADDED Requirements

### Requirement: Offline fixture builds need no unlocked build supply

Tracked Python fixture projects that offline quality tests build SHALL use uv's bundled build backend, through a requirement that the running uv satisfies, so a build needs nothing beyond the locked fixture supply. When that supply is complete, the state of uv's shared cache SHALL NOT change their verdict.

#### Scenario: The shared index lists an uncached build release

- **WHEN** another uv command has refreshed the shared index after a build dependency published a release, and offline tests build a fixture project
- **THEN** the build uses uv's bundled backend and downloads nothing

#### Scenario: The cache is empty

- **WHEN** a tracked fixture project is built offline from an empty uv cache
- **THEN** the build succeeds
