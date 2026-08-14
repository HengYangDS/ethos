## REMOVED Requirements

### Requirement: TransitionPlan Transition Contract

**Reason**: Reusable permissions and effect-only plans allow commands and
adapters to reconstruct missing lifecycle semantics independently.

**Migration**: Use operation-bound authority and the immutable transition
receipt contract.

## ADDED Requirements

### Requirement: Operation-bound authority contract

Commitment SHALL NOT carry reusable execution permissions. ETHOS SHALL derive
authority for exactly one operation and effect from the operation declaration,
actor facts, Commitment, prior Attestations, and fresh repository observations.

#### Scenario: An admitted receipt is reused for another effect

- **WHEN** any operation, actor, subject, binding, or effect differs from the
  receipt
- **THEN** apply rejects the receipt before mutation

#### Scenario: Commitment is inspected

- **WHEN** a Commitment carrier or schema is read
- **THEN** it contains intent, subjects, scope, invariants, acceptance, risks,
  authority references, hypotheses, and dependencies
- **AND** it contains no permission or mutable workflow field

### Requirement: Immutable transition receipt contract

The transition receipt SHALL bind the request, complete input digests, exact
operation authority, closed verdict, ordered gaps, preconditions, effects,
compensations, postconditions, and singular continuation in canonical bytes.

#### Scenario: Receipt bytes are changed after derivation

- **WHEN** apply validates a modified or non-canonical receipt
- **THEN** it blocks before any effect with a stable structured diagnostic

#### Scenario: Receipt has a blocking verdict

- **WHEN** the receipt verdict is not pass
- **THEN** no effect is executable
- **AND** the receipt exposes exactly one next action or explicit user decision

### Requirement: Commitment scope is positive and recursive

Commitment scope SHALL use positive repository-relative recursive patterns that
describe the intended semantic area. It SHALL support greenfield creation and
receipt-bound rebind without enumerating every future file or granting mutation
authority.

#### Scenario: A greenfield subtree is created

- **WHEN** a positive coarse scope covers a not-yet-existing nested path
- **THEN** recursive matching admits the path without a negative exception list
- **AND** sibling paths outside the declared area remain blocked

#### Scenario: Scope meaning changes

- **WHEN** an owned lane needs a different Commitment scope
- **THEN** one rebind receipt binds old and new bytes, semantic identity, head,
  tree, Lease generation, actor, and overlay before apply

### Requirement: Operation requests are context-independent values

Every operation request SHALL name repository identity and exact resource
coordinates explicitly. Host launch context, current directory basename,
environment history, personal path, or hidden global state SHALL NOT complete
missing request semantics.

#### Scenario: Hostile invocation context is supplied

- **WHEN** `PWD`, `OLDPWD`, process cwd, and editor root disagree
- **THEN** the declared repository and worktree bindings determine the request
- **AND** ambiguity blocks with one typed remediation
