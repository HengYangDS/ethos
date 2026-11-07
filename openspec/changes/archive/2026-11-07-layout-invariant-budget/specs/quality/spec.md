## ADDED Requirements

### Requirement: Python budget coordinates are layout-invariant

A Python coordinate with a declared tokens-per-line ratio SHALL be enforced in
line-equivalents: its layout-invariant code tokens divided by that ratio, rounded
up. Layout-invariant code tokens SHALL exclude comments, line structure,
standalone string expressions, statement semicolons and a comma directly before a
closing bracket. The physical-line measure SHALL remain the native cross-check's
comparison and the per-file ceiling's measure.

#### Scenario: Reformatting does not move an enforced Python coordinate

- **WHEN** a Python file is reformatted without changing its syntax tree, for
  example by joining a wrapped call onto one line and dropping its trailing comma
- **THEN** its layout-invariant code tokens and the enforced line-equivalents of
  its category are unchanged
- **AND** its physical-line measure may change for the cross-check and the
  per-file ceiling

#### Scenario: A category without a ratio keeps the line measure

- **WHEN** a Python category declares no tokens-per-line ratio
- **THEN** its limit is enforced on the physical-line measure
- **AND** a ratio that is not positive and finite, or names a category that is
  not Python, fails the policy closed
