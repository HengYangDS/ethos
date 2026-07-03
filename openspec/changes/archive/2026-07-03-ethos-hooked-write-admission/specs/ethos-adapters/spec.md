## ADDED Requirements

### Requirement: Hook Admission Runtime

ETHOS SHALL expose a hook-time admission report that binds write-capable
mutation attempts to Work Lane prewrite admission before filesystem mutation.

#### Scenario: Pre-tool protected-root mutation is blocked

- **WHEN** the hook admission runtime checks a tracked target path from an
  accepted root, candidate, submit lane, detached checkout, or unknown lane
- **THEN** ETHOS blocks the pre-tool decision before mutation
- **AND** the decision includes target root, editor root, checkout role, target
  paths, and the `protected_lane_prewrite_blocked` required gap.

#### Scenario: Pre-tool Work Lane mutation is admitted

- **WHEN** the hook admission runtime checks a tracked target path from a
  `work/*` lane whose editor root matches the checkout root
- **THEN** ETHOS admits the pre-tool decision
- **AND** includes the underlying `prewrite_guard` admission payload.

#### Scenario: Pre-run command risk requires admitted target paths

- **WHEN** a pre-run hook classifies a shell command as tracked-mutation risk
- **THEN** ETHOS blocks the command unless target paths are supplied and
  admitted by prewrite.

#### Scenario: Post-write protected-root mutation fuses the session

- **WHEN** a post-write hook observes a protected root with tracked dirty paths
- **THEN** ETHOS reports a fused decision
- **AND** includes required gaps for protected-root dirtiness or unexpected
  tracked paths.
