## MODIFIED Requirements

### Requirement: Accepted signature repair command

ETHOS SHALL expose bounded repair of explicitly selected incorrect commit identity
or signature. Readiness is effect-free. Authorized application SHALL preserve
non-selected content, retain verifiable originals, re-sign affected objects and
apply exact selected refs. Historical evidence SHALL NOT be relabeled current.

#### Scenario: Exact selection and backup

- **WHEN** an operator requests historical repair
- **THEN** readiness reports exact old identities, affected descendants and ref scope
- **AND** application requires unchanged coordinates and a verified recovery copy

#### Scenario: Only authorized bytes change

- **WHEN** historical identity repair replaces commits
- **THEN** trees, messages, timestamps and unselected identities remain unchanged
- **AND** parent order follows the verified mapping with current repair signatures

#### Scenario: Stale or interrupted repair

- **WHEN** refs drift or an effect acknowledgement is lost
- **THEN** repair rejects stale state or observes durable results before retry
- **AND** no unrelated refs or worktrees are rewritten

#### Scenario: Re-entry after repair

- **WHEN** rewritten history contains an officially archived Change
- **THEN** validated repair provenance preserves its exact intent bytes
- **AND** new proof, runtime binding and each peer publication are verified separately

#### Scenario: Continued history retains archived intent

- **WHEN** later commits descend from a completed repair or a sequence of completed repairs
- **THEN** archive resolution follows validated object mappings and native ancestry
- **AND** it preserves the original archive acceptance without requiring the current HEAD to be a repair result
- **AND** missing effect evidence or ambiguous replacement paths cannot supply archive authority

#### Scenario: Readiness has no signing effect

- **WHEN** an operator requests signature-repair readiness for an exact accepted head
- **THEN** ETHOS reports current prerequisites and the authorized apply action
- **AND** it does not create a replacement object or move refs or worktrees

#### Scenario: Application requires authorization

- **WHEN** repair application lacks explicit authorization or has stale coordinates
- **THEN** it rejects the request before creating a replacement object
- **AND** it identifies the failed boundary and one fresh next action

#### Scenario: Successful repair requires new proof

- **WHEN** the selected local repair effects finish and their postconditions hold
- **THEN** the result identifies the replacement commit and exact reproof command
- **AND** it does not claim proof, runtime activation or remote publication

#### Scenario: Recovery observes instead of repeating effects

- **WHEN** a signing or ref effect has completed but its acknowledgement was lost
- **THEN** recovery uses durable result evidence and current Git observations
- **AND** it does not create another replacement or repeat completed effects
- **AND** missing evidence remains unknown rather than implying completion
