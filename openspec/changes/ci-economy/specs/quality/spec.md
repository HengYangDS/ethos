## MODIFIED Requirements

### Requirement: Each Forge verifies a published commit once

Hosted CI SHALL verify a commit published to both Forges once per plane: GitHub SHALL run every
commit-scoped job, and GitLab SHALL run commit-range admission and conformance. GitLab SHALL run
every commit-scoped job for a merge request, for a `main` whose tree differs from `dev`, and for a
batch-head or scheduled pipeline. A push of `main` to the commit that `dev` carries SHALL repeat no
commit-scoped job. Each Forge SHALL admit one commit range per push, pull-request or merge-request
event.

#### Scenario: GitHub main follows dev

- **WHEN** `main` is pushed to GitHub
- **THEN** its run executes only the commit-range admission of the pushed range and the aggregate
  check
- **AND** host conformance, quality gates and external links stay with `dev`'s run of that commit

#### Scenario: GitLab main has dev's tree

- **WHEN** `main` is pushed to GitLab with the tree of `dev`
- **THEN** its pipeline runs only commit policy
- **AND** the commit-scoped jobs stay with `dev`'s pipeline of that commit

#### Scenario: GitLab main differs from dev

- **WHEN** `main` is pushed to GitLab with a tree that differs from `dev`
- **THEN** its pipeline runs every commit-scoped job

#### Scenario: Other events keep the full verification

- **WHEN** `dev` or a proposal ref is pushed to GitHub, or a pull or merge request is opened or
  updated
- **THEN** that Forge runs every commit-scoped job and admits the event's range once

#### Scenario: A proposal leaves Windows on Arm to the landed commit

- **WHEN** a proposal ref is pushed
- **THEN** GitHub runs every commit-scoped job except the Windows host conformance legs, the
  emulated Windows on Arm leg among them, and admits the event's range
- **AND** that leg runs for the landed commit, when a dispatch qualifies the batch head or the
  drift schedule runs
- **AND** only a newer push of the same proposal ref cancels those jobs

#### Scenario: A push leaves the Windows legs to a typed dispatch

- **WHEN** `dev` or a proposal ref is pushed
- **THEN** GitHub runs every commit-scoped job without a Windows host conformance leg, native or
  emulated, and admits the event's range
- **AND** a dispatch that asks for the Windows legs, or that qualifies a batch head, runs them
- **AND** only a newer push of the same proposal ref cancels those jobs

#### Scenario: GitLab observes a ref published to both Forges

- **WHEN** `dev` or a proposal ref is pushed to GitLab
- **THEN** its pipeline runs commit policy, host conformance and the npm package tests
- **AND** it runs neither the full gate set nor external links, which GitHub's run of that commit
  executes

#### Scenario: A batch head is qualified on GitLab

- **WHEN** a `web` or `api` pipeline starts on a proposal ref and declares the head it qualifies
- **THEN** a pipeline whose commit is that head runs every commit-scoped job
- **AND** a pipeline whose commit differs from that head is not created

#### Scenario: A scheduled pipeline observes drift

- **WHEN** a pipeline schedule runs on GitLab
- **THEN** its pipeline runs every commit-scoped job and admits no range

### Requirement: Hosted test feedback is visible and source bound

Each hosted projection SHALL publish test-owned JUnit and coverage artifacts from every run that
executes the test gate, including outputs available after failure. GitLab SHALL declare native test
and coverage reports for them. GitHub SHALL expose a native job summary with the exact source, proof
outcome and available test observations. A run without the test gate SHALL declare no test report.
Reporting SHALL NOT mint proof, hide failed execution or fabricate successful missing observations.

#### Scenario: A hosted test fails

- **WHEN** a test run produces failing JUnit results
- **THEN** available reports remain uploaded and inspectable
- **AND** the hosted job retains its non-passing execution result

#### Scenario: Test observations are unavailable

- **WHEN** JUnit or coverage output is missing or malformed
- **THEN** the summary explicitly identifies unavailable observations
- **AND** it does not substitute zero tests or a passing coverage result

#### Scenario: GitLab observes a published ref without the test gate

- **WHEN** GitLab runs admission and conformance for a pushed `dev` or proposal ref
- **THEN** its pipeline declares no JUnit or coverage report
- **AND** GitHub's run of that commit publishes them

### Requirement: Hosted check names are stable identities

Each job that a hosted CI projection generates SHALL take its name from its matrix coordinates and
fixed text alone, and a matrix SHALL name a platform by its platform id, never by its runner label.
A supply, tool or runner-label change SHALL NOT rename a job, so the required checks that a forge
declares keep naming the jobs that report them.

#### Scenario: A locked runtime version changes

- **WHEN** the locked Node version changes
- **THEN** every projected job keeps its name

#### Scenario: A matrix job is projected

- **WHEN** a job runs over the platform and `python` coordinates
- **THEN** its name is formed from those two coordinates and fixed text, such as
  `linux-x64 / Python 3.12`

#### Scenario: A runner label changes

- **WHEN** the runner label that provides a platform changes
- **THEN** every projected job keeps its name

### Requirement: A newer proposal push supersedes its earlier run

A newer push of a proposal ref, or to a pull or merge request, SHALL cancel the hosted run of its
earlier push, whose head is no longer proposed. No newer event SHALL cancel or queue a run of `dev`
or `main`, a scheduled run, or a manual dispatch such as a release or a batch-head qualification.

#### Scenario: A proposal ref is pushed again

- **WHEN** a proposal ref is pushed again while the run of its earlier push is in progress
- **THEN** the Forge cancels the earlier run's jobs
- **AND** the newer push's run executes every job of its role and tier and admits its range

#### Scenario: A pull or merge request is pushed again

- **WHEN** a pull or merge request receives a newer push while the run of its earlier push is in
  progress
- **THEN** the Forge cancels the earlier run's jobs

#### Scenario: Other runs are never superseded

- **WHEN** `dev` or `main` is pushed, a schedule fires, or a manual dispatch runs
- **THEN** no later event cancels or queues its run

## ADDED Requirements

### Requirement: Hosted host conformance runs in declared tiers

Hosted CI SHALL run host conformance in tiers. A push or pull request SHALL run Linux x64 at every
supported Python version and one macOS arm64 leg at the lowest. The full matrix, every supported
platform at every version with the Windows legs, SHALL run only for a batch-head dispatch that names
the head it qualifies and for a drift schedule. A typed dispatch input SHALL add the Windows legs to
a push tier. A dispatch whose named head differs from its commit SHALL fail.

#### Scenario: A push runs the push tier

- **WHEN** `dev` or a proposal ref is pushed to GitHub
- **THEN** host conformance runs on Linux x64 at each supported Python version and on macOS arm64 at
  the lowest
- **AND** no other host conformance leg runs

#### Scenario: A batch head is qualified on GitHub

- **WHEN** a dispatch names the head it qualifies and runs at that commit
- **THEN** host conformance runs on every supported platform at every supported Python version, the
  Windows legs included

#### Scenario: A dispatch names a stale head

- **WHEN** a dispatch names a head that differs from the commit it runs at
- **THEN** no commit-scoped job runs
- **AND** the aggregate check fails

#### Scenario: The lane owner asks for the Windows legs

- **WHEN** a dispatch sets the Windows input without naming a head
- **THEN** the push tier and the Windows legs run

### Requirement: One aggregate check reports the per-push jobs

GitHub's projection SHALL carry one aggregate job, `hosted checks`, that needs every required
per-push job, commit-range admission included, and runs whatever their results. It SHALL pass only
when each needed job succeeded where its event runs it and was skipped only where its event has no
such job: a `main` push that follows `dev`, and admission on a dispatch or schedule. It SHALL NOT
need the external link observation, which may fail. Its result is a host observation, not
repository proof.

#### Scenario: A per-push job fails

- **WHEN** commit-range admission, a host conformance leg or the quality gates job fails or is
  cancelled
- **THEN** `hosted checks` fails

#### Scenario: A job is skipped on a commit run

- **WHEN** a push of `dev` or a proposal ref, or a pull request, ends with a needed job skipped
- **THEN** `hosted checks` fails

#### Scenario: An event has no such job

- **WHEN** `main` follows `dev` and its admission succeeds, or a batch-head dispatch or the drift
  schedule ends with every commit-scoped job successful
- **THEN** `hosted checks` succeeds with the jobs that the event does not have skipped

#### Scenario: The external link observation fails

- **WHEN** external link health finds an unreachable or redirecting link while every required
  per-push job succeeds
- **THEN** its job keeps its report and fails by its declared tolerance without failing the run
- **AND** `hosted checks`, which neither needs that job nor reads its result, succeeds

### Requirement: Hosted jobs bound their time and credentials

Every hosted job SHALL declare a timeout for its job class, set from the measured duration of that
class and above the longest timeout of the gates it runs. No hosted checkout SHALL persist its
credentials. Every action that a workflow uses SHALL be pinned to a full commit id that the tracked
workflow lockfile records. A job's permissions SHALL exceed read access only in a release job or the
supply-image job.

#### Scenario: A gate's timeout reaches its job's timeout

- **WHEN** a gate declares a timeout at or above the timeout of a job class that runs it
- **THEN** the CI model does not compile, and the projection check reports the class and the gate

#### Scenario: A checkout is projected

- **WHEN** a hosted job checks out the repository
- **THEN** its checkout declares that credentials are not persisted

#### Scenario: An action pin has no lock entry

- **WHEN** a workflow uses an action whose commit the workflow lockfile does not record
- **THEN** the architecture regression fails

#### Scenario: A verification job widens its permissions

- **WHEN** a job other than a release job or the supply-image job declares a permission beyond read
  access
- **THEN** the architecture regression fails

### Requirement: Hosted download caches have one writer

GitHub's verification jobs SHALL restore download caches keyed on the runner's system and
architecture, the Python version and the lockfiles, and SHALL NOT take the supply image. Only the
scheduled run of `main` SHALL write those caches, after pruning them to downloaded material. A
release job SHALL neither read nor write a cache, and a restored cache SHALL NOT replace the locked
verification of what it holds.

#### Scenario: A proposal run restores a cache

- **WHEN** a proposal ref is pushed and the scheduled run of `main` wrote a cache for its lockfiles
- **THEN** its jobs restore that cache and write none

#### Scenario: A lockfile changes

- **WHEN** a lockfile differs from the one the cache was keyed on
- **THEN** the job restores nothing and downloads from its locked sources

#### Scenario: A release job runs

- **WHEN** a release, journey or binary scan job runs
- **THEN** it declares no cache step
