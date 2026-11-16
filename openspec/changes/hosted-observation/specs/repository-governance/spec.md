## ADDED Requirements

### Requirement: Hosted runs of one head are read on every CI peer

ETHOS SHALL read the hosted runs of one exact commit from each declared peer with the `ci_cd`
capability through that provider's authenticated CLI. A run's own conclusion SHALL decide the run.
The jobs of a run that failed or still runs SHALL be read and those that did not pass listed, a
job that the pipeline lets fail told apart. An answer that cannot be used SHALL be `unknown`,
never a pass. The observation SHALL be read each time, SHALL record nothing and SHALL mint no
authority.

#### Scenario: A CI peer holds no run of the head

- **WHEN** `ethos publish --observe-hosted --json` runs and a CI peer lists no run of the
  worktree's head, or only skipped ones
- **THEN** that peer's state is `no_run` and the result carries `hosted_run_missing:<peer>`
- **AND** the verdict is `block` and the next action is that gap's registered repair

#### Scenario: A run has not concluded

- **WHEN** a CI peer's run of the head is queued or running and none of its runs failed
- **THEN** that peer's state is `running` and the result carries `hosted_run_running:<peer>`
- **AND** the verdict is `unknown`, and the next step is the same observation while no peer is
  failed, without a run or unknown

#### Scenario: Every run passed

- **WHEN** every CI peer lists at least one run of the head and each run that ran concluded as
  passed
- **THEN** the verdict is `pass`, the state is `passed` and the result carries no gap
- **AND** each run is one row with its identity and its conclusion, and no job is read: the
  observation costs one provider call for each CI peer

#### Scenario: A job failed the run

- **WHEN** a run of the head concluded as failed on a CI peer
- **THEN** that peer's state is `failed` and the result carries `hosted_run_failed:<peer>`
- **AND** the verdict is `block`, also when another run of that peer is still running
- **AND** the run lists its jobs that failed or still run, and no job that passed or was skipped

#### Scenario: A job is allowed to fail

- **WHEN** a job failed and its run concluded as passed all the same
- **THEN** the run is `passed`, and a peer whose runs passed is `passed`
- **AND** in a run that did not pass, a failed job that the provider marks as allowed to fail is
  listed as `allowed_failure`

#### Scenario: Two CI peers disagree

- **WHEN** one CI peer's runs passed and another failed, holds no run, is running or is unknown
- **THEN** `data.hosted_observation.peers` states each peer on its own
- **AND** the gaps name only the peers that did not pass, and the verdict is `block` when a peer
  failed or holds no run

#### Scenario: The forge gives no usable answer

- **WHEN** the provider's CLI is absent, has no credentials, exceeds its time, prints what cannot
  be parsed or answers for another commit, or the peer's web repository is not resolved
- **THEN** that peer's state is `unknown` with a reason and a next action, and no stderr
- **AND** the result carries `hosted_run_unknown:<peer>` and its verdict is never `pass`
- **AND** the next action names the query that failed, never one that answered

#### Scenario: The reader cannot use the forge's answer

- **WHEN** the provider's answer names another commit, a run without an identity or a state
  outside the reader's table, or fills a page, or the peer's provider has no reader
- **THEN** that peer's next action is a step by hand, and no query is named again

#### Scenario: Two peers decide differently

- **WHEN** one CI peer holds no run of the head and another cannot be read
- **THEN** the result blocks, its first gap names the peer without a run, and its next action is
  that gap's repair

#### Scenario: No CI peer is declared

- **WHEN** the repository declares no peer with the `ci_cd` capability
- **THEN** the observation runs no provider command and passes in the state `no_ci_peer`
- **AND** its summary counts zero CI peers

#### Scenario: The publication declaration cannot be observed

- **WHEN** the release binding cannot be read or declares an invalid peer or a retired field
- **THEN** the result blocks in the state `topology_invalid` with the declaration's own gaps
- **AND** its next action is the topology's repair where it names one, and never empty
- **AND** the observation under `data.hosted_observation` carries the same next action

#### Scenario: The observation is asked for another head

- **WHEN** `--expect-head` names a commit other than the worktree's head
- **THEN** the result is `block` with `expect_head_mismatch` and no provider command runs

### Requirement: The landing preview states the hosted observation

`ethos land --json` SHALL state the hosted observation of the lane head on every CI peer under
`data.hosted_observation`, with each peer's state and the gaps under `observation_gaps`. The
observation SHALL NOT change the preview's verdict, its required gaps or its next action, and an
apply SHALL NOT read it.

#### Scenario: The preview observes and does not refuse

- **WHEN** `ethos land --json` previews a head that one CI peer holds no run of and another failed
- **THEN** `data.hosted_observation` names both peers' states and both gaps
- **AND** the preview's verdict and required gaps equal those of a head whose runs passed

#### Scenario: An apply reads no forge

- **WHEN** `ethos land --apply` runs
- **THEN** its result carries no hosted observation and no provider command runs for it

### Requirement: The probe of a release ref states the hosted observation

`ethos publish --ref <ref> --probe-remote` SHALL state the hosted observation of its proof head
under `data.hosted_observation` when a target ref is the release branch or a release tag. The
observation SHALL NOT change the probe's verdict, its required gaps or its derived request. A
probe of any other ref, a retirement and a receipt's apply SHALL NOT read it.

#### Scenario: A release ref's probe observes and does not refuse

- **WHEN** the release branch is probed for a head that one CI peer holds no run of and another
  failed
- **THEN** `data.hosted_observation` names the proof head, both peers' states and both gaps
- **AND** the probe's verdict and required gaps equal those of a head whose runs passed

#### Scenario: Another ref's probe reads no forge

- **WHEN** the accepted branch or a proposal ref is probed
- **THEN** the result carries no hosted observation and no provider command runs for it
