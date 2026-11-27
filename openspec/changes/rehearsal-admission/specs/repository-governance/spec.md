## ADDED Requirements

### Requirement: The hosted observation states a head's rehearsal

Where the release binding names a rehearsal peer, the explicit hosted observation SHALL state the
rehearsal of the observed head: the newest dispatched run of that commit on that peer that ran
the rehearsal's verdict job, with that job's conclusion as its state. An answer that cannot be
used SHALL be `unknown`, never a pass. The reading SHALL record nothing, SHALL mint no authority
and SHALL NOT change the observation's verdict, gaps or next action.

#### Scenario: The newest rehearsal passed

- **WHEN** `ethos publish --observe-hosted --json` runs for a head whose newest rehearsal's
  verdict job succeeded
- **THEN** the observation's rehearsal names the peer, the run and its attempt with the state
  `passed`
- **AND** it carries no gap for the rehearsal.

#### Scenario: A newer rehearsal failed after an older one passed

- **WHEN** the head has two rehearsals and the newer one's verdict job failed
- **THEN** the rehearsal's state is `failed`
- **AND** it carries `release_rehearsal_unproven:failed`.

#### Scenario: No run of the head ran the verdict job

- **WHEN** the peer lists runs of the head and none of its dispatched runs ran the verdict job
- **THEN** the rehearsal's state is `missing` and it carries `release_rehearsal_unproven:missing`
- **AND** the result's verdict and required gaps equal those of the same head without the opt-in.

#### Scenario: A dispatched run has not concluded

- **WHEN** a dispatched run of the head is queued or running
- **THEN** the rehearsal's state is `running` and it carries `release_rehearsal_unproven:running`.

#### Scenario: The forge gives no usable answer

- **WHEN** the listing or the read of a run's jobs is refused, late, unparsable or about another
  commit
- **THEN** the rehearsal's state is `unknown` and it carries `release_rehearsal_unproven:unknown`.

#### Scenario: The binding names no rehearsal peer

- **WHEN** the release binding declares no rehearsal table
- **THEN** the observation carries no rehearsal and no provider command runs for one.

### Requirement: The probe of a release tag reports its head's rehearsal

`ethos publish --ref <tag> --probe-remote` SHALL state the rehearsal of its proof head with the
hosted observation when a target ref is a release tag and the release binding names a rehearsal
peer. While the rule `release_rehearsal_unproven` is in the reporting state, the probe's verdict,
required gaps and derived request SHALL be what they are without the rehearsal. A probe of any
other ref, a landing preview, a retirement and an apply SHALL read no rehearsal.

#### Scenario: A release tag is probed for a head without a rehearsal

- **WHEN** a release tag is probed, the binding names a rehearsal peer and the tagged head has no
  rehearsal
- **THEN** `data.hosted_observation` carries the rehearsal with the state `missing` and its gap
- **AND** the probe's verdict and required gaps equal those of a rehearsed head.

#### Scenario: The release branch is probed

- **WHEN** the release branch is probed
- **THEN** the hosted observation carries no rehearsal and no provider command runs for one.
