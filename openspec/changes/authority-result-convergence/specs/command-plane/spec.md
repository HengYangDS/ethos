## ADDED Requirements

### Requirement: Current repository decisions have one resolution owner

ETHOS SHALL resolve current role, actor, Lease, fresh Git facts, selected
official OpenSpec intent, first exact gap, and recovery action once for each
operation. Status, plan, prewrite, and hook surfaces SHALL consume that typed
resolution without reclassifying its authority, gap, or next action.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, and a hook evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

### Requirement: Continuation derives from explicit result facts

The schema-version-`2` result SHALL carry `user_decision_required` as an
explicit typed fact selected by the owning resolution. `continuation` SHALL be a
pure projection from verdict, the presence of the sole next action, and that
fact. ETHOS SHALL NOT infer an authority boundary by parsing command text,
English phrases, or gap-name suffixes.

#### Scenario: A mutating-looking command is already authorized

- **WHEN** a result exposes an executable next action and explicitly states that no user decision is required
- **THEN** `user_decision_required` remains false
- **AND** Continuation is `continue` for a passing result or `blocked` for a non-passing result

#### Scenario: Human authority is required

- **WHEN** the owning resolution explicitly marks that handoff, authorization, or confirmation is required
- **THEN** `user_decision_required` is true
- **AND** Continuation is `await-user` without inspecting the action string or gap spelling

### Requirement: Result projection preserves diagnostic execution facts

When a command cannot resolve or execute a required tool or projection, the
owning resolution SHALL preserve the exact boundary facts needed to recover,
including the attempted binary or route, cwd, captured stderr, and relevant
environment projection. A projection failure SHALL NOT be relabeled as adoption
failure or product-test failure.

#### Scenario: Official projection is unavailable from the working tree

- **WHEN** official OpenSpec artifacts exist but the selected projection cannot be read
- **THEN** the result identifies the exact OpenSpec command, cwd, exit status, and stderr
- **AND** the sole next action repairs or completes that projection rather than running `ethos adopt`

#### Scenario: A continuation route is unsupported

- **WHEN** a continuation token is sent to the wrong execution route or a capability is unavailable
- **THEN** the structured result distinguishes wrong route, unavailable capability, and provider finalization failure
- **AND** it states whether mutation occurred and names the sole safe continuation without replaying the mutation
