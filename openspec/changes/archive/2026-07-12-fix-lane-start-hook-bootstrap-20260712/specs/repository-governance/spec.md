## ADDED Requirements

### Requirement: Fresh Work Lane bootstrap avoids unnecessary runtime admission

ETHOS SHALL allow Git to create or reassert a fresh Work Lane ref without
materializing a checkout-local Python runtime when the ref does not change.
This exception SHALL be limited to a `work/*` branch with an absent selected
local runtime and either a zero old object ID or equal old and new object IDs.

#### Scenario: Fresh Work Lane ref is reasserted without a runtime

- **GIVEN** Git is creating a linked Work Lane checkout
- **AND** the reference-transaction event creates the Work Lane ref from the
  zero object ID or reasserts equal old and new object IDs
- **AND** the checkout-local runtime interpreter is absent
- **WHEN** the reference-transaction hook evaluates that event
- **THEN** it completes the non-accepted no-op event without invoking runtime
  materialization
- **AND** `ethos lane start --apply` can create the Work Lane and then acquire
  its lease without requiring network access.

#### Scenario: Protected and changed refs retain ordinary admission

- **WHEN** the reference-transaction event targets the accepted branch,
  changes an existing Work Lane ref, or targets a non-Work-Lane branch
- **THEN** ETHOS SHALL retain the existing runtime-backed admission path
- **AND** accepted-root admission remains fail-closed
- **AND** a committed changed Work Lane ref retains lease-head repair.
