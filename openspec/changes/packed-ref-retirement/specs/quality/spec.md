## ADDED Requirements

### Requirement: A deletion without an old value is governed by the ref's value

When a prepared reference transaction reports a governed ref with zero old and new values, as Git
does for a deletion without an old value and for the packed-refs twin of a deletion, the hook SHALL
govern it as the deletion of that ref's current value. A ref that does not exist SHALL keep the zero
values.

#### Scenario: A packed absorbed ref is retired

- **GIVEN** a Work Lane ref that `packed-refs` holds and whose contribution the accepted root has
- **WHEN** its prepared absorbed-ref retirement deletes it under the generated hooks
- **THEN** the hook admits both the packed transaction's line and the main transaction's line
- **AND** the ref is retired.

#### Scenario: A protected branch is deleted without an old value

- **WHEN** `git update-ref -d` deletes the accepted branch without its old value
- **THEN** the hook refuses it under the accepted branch's rules, not for a missing policy
- **AND** the branch keeps its value.
