# repository-governance Delta

## MODIFIED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, and SHALL expose Work Lane
coordination small signals in focused reader summaries without granting foreign
lane authority. In productized multi-human and multi-agent operation, Work Lane
lease ownership SHALL identify the concrete acting holder rather than only a
provider class.

#### Scenario: Foreign Work Lanes are observable but not owned by the current actor

- **GIVEN** a repository has a linked foreign `work/*` worktree
- **WHEN** `ethos status --json` reports that lane in `data.foreign_work_lanes`
- **THEN** the lane item exposes `current_actor_capability=observe`
- **AND** `allowed_actions` contains only `observe`
- **AND** `forbidden_actions` includes `write`, `land`, and `retire`
- **AND** write authority remains owner-only
- **AND** retirement requires the owner, accepted handoff, or maintainer
  break-glass evidence
- **AND** a provider label such as `codex` is not sufficient by itself to prove
  that the current actor owns another Codex thread's Work Lane

#### Scenario: lane lease holder identifies a concrete acting instance

- **GIVEN** a Work Lane lease is created or renewed in a multi-agent repository
- **WHEN** ETHOS records or reports the lease holder
- **THEN** the holder is represented by a provider-neutral concrete reference
  such as `agent:codex:thread:<id>`, `agent:claude:chat:<id>`,
  `agent:jetbrains:chat:<id>`, `human:shell:<id>`, or
  `service:gitlab-ci:pipeline:<id>`
- **AND** a bare provider or actor class such as `codex`, `claude`, `cursor`, or
  `ci` is treated as a legacy hint rather than sufficient ownership authority
- **AND** compatibility fields such as `lease_owner` may be exposed during
  migration only when they do not override the concrete holder reference

#### Scenario: authority policy owns role capability

- **GIVEN** a lease holder requests write, land, retire, handoff, or break-glass
  authority
- **WHEN** ETHOS evaluates the request
- **THEN** the Lane Lease identifies the temporary holder
- **AND** Authority policy determines the holder's roles and capabilities
- **AND** claim, scope, evidence, and current Git state determine whether the
  requested action is admissible
- **AND** ETHOS does not require a first-class Principal, Actor, Participant,
  Party, Session, or Agent registry to make the decision

## ADDED Requirements

### Requirement: Work Lane Lifecycle Resolution

ETHOS SHALL record durable Work Lane lifecycle judgments as evidence-bound
Chronicle events rather than as a separate lane-resolution truth store.

#### Scenario: lane handoff is recorded as Chronicle resolution

- **GIVEN** a Work Lane is transferred from one concrete holder to another
- **WHEN** the handoff is accepted
- **THEN** ETHOS records a `lane_resolution` Chronicle event for that lane
- **AND** the event includes the resolution kind, previous holder, next holder,
  decision authority, evidence references, and decision result
- **AND** the Chronicle event does not replace the active Lane Lease state used
  for current write admission

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has a missing, stale, ambiguous, or legacy provider-only
  holder
- **WHEN** ETHOS audits the lane for closeout or cleanup
- **THEN** ETHOS treats orphan-like facts as evidence requiring a resolution
  decision
- **AND** the durable outcome is a Chronicle `lane_resolution` with kind such as
  `retire`, `preserve`, `block`, `handoff`, or `break_glass`
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted
