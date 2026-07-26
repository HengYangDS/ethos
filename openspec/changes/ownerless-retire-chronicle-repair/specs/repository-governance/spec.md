## ADDED Requirements

### Requirement: Direct-retire Chronicle authority is effect-admissible before retry

ETHOS governance SHALL require a successor accepted Chronicle before retrying a
direct-retire effect whose prior decision reached no effect because the accepted
Chronicle did not satisfy the current effect-side disposition contract. The
successor SHALL bind the exact prior decision and gap, preserve that decision as
non-reusable history, name one exact target branch and head, and include the
literal `lane_resolution/retire` effect token as its own line.

#### Scenario: accepted Chronicle repair precedes a new direct-retire decision

- **GIVEN** a recorded direct-retire decision has no package, receipt, ref, or
  worktree effect and inventory reports it as pending
- **AND** effect apply returned
  `lane_resolution_ownerless_chronicle_invalid`
- **WHEN** a successor accepted carrier repairs the target Chronicle contract
- **THEN** the failed decision SHALL remain immutable and non-reusable
- **AND** a retry SHALL use a new target-bound Chronicle digest and decision ID
- **AND** effect admission SHALL reach later target checks without bypassing
  accepted ancestry, owner, dirtiness, registration, or Chronicle validation.

#### Scenario: identical unattempted target is repaired without manufacturing failure

- **GIVEN** a second exact target uses the same invalid Chronicle authoring
  shape but has not executed an effect
- **WHEN** the successor carrier adds its effect-admissible Chronicle
- **THEN** governance SHALL NOT create a knowingly invalid decision merely to
  duplicate the first failure
- **AND** the second target SHALL still require a fresh decision, observation,
  and native effect result after successor acceptance.
