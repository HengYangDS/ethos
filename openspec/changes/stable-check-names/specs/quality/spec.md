## ADDED Requirements

### Requirement: Hosted check names are stable identities

Each job that a hosted CI projection generates SHALL take its name from its matrix coordinates and fixed text alone. A supply or tool version change SHALL NOT rename a job, so the required checks that a forge declares keep naming the jobs that report them.

#### Scenario: A locked runtime version changes

- **WHEN** the locked Node version changes
- **THEN** every projected job keeps its name

#### Scenario: A matrix job is projected

- **WHEN** a job runs over the `os` and `python` axes
- **THEN** its name is formed from those two axes and fixed text, such as `ubuntu-latest / Python 3.12`
