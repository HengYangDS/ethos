## ADDED Requirements

### Requirement: Current-policy proof coexists with immutable superseded proofs

When several current same-HEAD proof records exist, ETHOS SHALL select only
records whose complete plan and evidence match the current canonical proof
policy, source intent, repository identity and required floor. An internally
valid record from a superseded policy SHALL remain immutable historical
evidence but SHALL NOT veto a separate valid current-policy proof. It SHALL NOT
itself satisfy the current query. Invalid envelope, artifact or statement
bindings, and conflicting applicable proofs, SHALL retain their fail-closed
behavior.

#### Scenario: Current proof follows a policy upgrade

- **GIVEN** one exact commit has an internally valid proof under an earlier
  policy and another under the current canonical policy
- **WHEN** a repository transition selects proof for that commit
- **THEN** the current-policy proof may be admitted without deleting or
  rewriting the old record
- **AND THEN** the selected proof still binds the exact source, current intent
  and required floor.

#### Scenario: Only an old policy proof remains

- **WHEN** an exact commit has no proof matching the current canonical policy
- **THEN** proof admission reports the policy mismatch and blocks the
  transition.

#### Scenario: Caller selects an old record explicitly

- **WHEN** a caller selects an internally valid old-policy Attestation ID
- **THEN** ETHOS rejects that selection as insufficient current proof
- **AND THEN** it does not silently substitute a different record.

#### Scenario: Malformed or conflicting evidence remains blocking

- **WHEN** any current same-HEAD record has a broken envelope, artifact or
  statement binding, or applicable current-policy records conflict
- **THEN** a separate valid current proof does not hide that defect
- **AND THEN** no publication or accepted-ref effect is admitted from the set.
