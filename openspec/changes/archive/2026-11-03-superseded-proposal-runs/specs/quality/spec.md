## ADDED Requirements

### Requirement: A newer proposal push supersedes its earlier run

A newer push of a proposal ref SHALL cancel the hosted run of its earlier push, whose head the ref
no longer proposes. No newer event SHALL cancel or queue a run of `dev` or `main`, of a manual
dispatch such as a release, or of a pull or merge request.

#### Scenario: A proposal ref is pushed again

- **WHEN** a proposal ref is pushed again while the run of its earlier push is in progress
- **THEN** the Forge cancels the earlier run's jobs
- **AND** the newer push's run executes every commit-scoped job and admits its range

#### Scenario: Other runs are never superseded

- **WHEN** `dev` or `main` is pushed, a manual dispatch runs, or a pull or merge request is opened
  or updated
- **THEN** no later event cancels or queues its run

## MODIFIED Requirements

### Requirement: Each Forge verifies a published commit once

Hosted CI SHALL run the commit-scoped jobs of a published commit once on each Forge: a push of
`main` to the commit that `dev` carries SHALL NOT repeat the jobs that `dev`'s run of that commit
executes, and every pushed ref SHALL keep its own commit-range admission. Because `main` moves only
to the exact accepted commit, GitHub SHALL decide by the event, and GitLab by comparing `main`'s
tree with `dev`.

#### Scenario: GitHub main follows dev

- **WHEN** `main` is pushed to GitHub
- **THEN** its run executes only the commit-range admission of the pushed range
- **AND** host conformance, quality gates, external links, repository proof and package artifacts
  stay with `dev`'s run of that commit

#### Scenario: GitLab main has dev's tree

- **WHEN** `main` is pushed to GitLab with the tree of `dev`
- **THEN** its pipeline runs only commit policy
- **AND** the commit-scoped jobs stay with `dev`'s pipeline of that commit

#### Scenario: GitLab main differs from dev

- **WHEN** `main` is pushed to GitLab with a tree that differs from `dev`
- **THEN** its pipeline runs every commit-scoped job

#### Scenario: Other events keep the full verification

- **WHEN** `dev` or a proposal ref is pushed, or a pull or merge request is opened or updated
- **THEN** the Forge runs every commit-scoped job and admits the event's range
- **AND** only a newer push of the same proposal ref cancels those jobs
