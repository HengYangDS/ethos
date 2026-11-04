## ADDED Requirements

### Requirement: Generated Windows verification jobs retry their source checkout

The common CI model SHALL set GitLab's `GET_SOURCES_ATTEMPTS` to `"3"` on every Windows verification job that it generates, and a runner declaration SHALL NOT change that value.

#### Scenario: A Windows job starts while files of the previous job are still held

- **WHEN** a generated Windows verification job's source checkout fails because `git clean` cannot yet remove the previous job's executables
- **THEN** GitLab retries the source checkout up to three attempts before the job fails

#### Scenario: A runner declares another number of attempts

- **WHEN** a Windows runner declaration sets `GET_SOURCES_ATTEMPTS` to another value
- **THEN** compiling the projections fails and no projection is written
