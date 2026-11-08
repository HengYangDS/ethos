## MODIFIED Requirements

### Requirement: Admission Before Product Audit

ETHOS SHALL evaluate apply-mode mutation admission before running product repository-audit checks.

#### Scenario: Apply mode is blocked by lane admission

- **WHEN** `ethos land --apply` is invoked from a protected root with explicit authorization and
  expected HEAD
- **THEN** ETHOS returns structured `blocked` JSON with `protected_root_mutation`
- **AND** ETHOS does not require the target repository to contain ETHOS product repository
  governance schemas before reporting the admission failure

### Requirement: Exact-request Mutation Admission

Only a `pass` verdict may authorize an effect; `block` and `unknown` both fail closed.

ETHOS SHALL block apply-mode land and publish unless execution confirmation, expected HEAD binding,
applicable Commitments, current facts, and required Evidence admit the exact request. Confirmation
SHALL NOT authenticate a caller or create reusable authorization.

#### Scenario: Apply mode is requested

- **WHEN** `ethos land --apply` or `ethos publish --receipt <path> --apply` runs
- **THEN** ETHOS requires explicit confirmation and expected HEAD before any mutation can proceed
- **AND** the decision binds action, resource, expected state, policy refs, evidence refs, and
  decision basis
- **AND** it mints no role, token, session, or reusable permission.
