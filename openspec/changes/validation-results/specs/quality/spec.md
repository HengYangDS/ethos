## ADDED Requirements

### Requirement: Native Validation Outcomes Preserve Failure Meaning

ETHOS SHALL require both successful native validation execution and a readable
full validation result before accepting it. A failed exit SHALL remain a failure
without item diagnostics. Any invalid item SHALL remain a failure even when the
process exits successfully. Malformed consumed fields SHALL prevent acceptance.

#### Scenario: Failed execution has no item-level explanation

- **WHEN** the native validator exits unsuccessfully with empty or missing items
- **THEN** the public report retains a validation failure and its original result.

#### Scenario: A successful exit contradicts an invalid item

- **WHEN** the native process exits zero but one item has valid set to false
- **THEN** the public report rejects that item rather than accepting the exit code.

#### Scenario: The reported collection cannot establish item validity

- **WHEN** items or their consumed identity and validity fields are malformed
- **THEN** the public report identifies unreadable validation rather than omitting them.

### Requirement: Informational Native Findings Remain Informational

ETHOS SHALL preserve successful empty full reports and valid items containing
informational findings. It SHALL consume the official validity decision instead
of converting every issue into an error or reimplementing native spec semantics.

#### Scenario: Official validation succeeds with informational findings

- **WHEN** a successful full result contains only valid items with INFO findings
- **THEN** ETHOS accepts that validation while retaining the original findings.

#### Scenario: Official validation has no items

- **WHEN** a successful native full result declares an empty items collection
- **THEN** ETHOS accepts the empty validation without inventing an invalid Change.
