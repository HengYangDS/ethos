## REMOVED Requirements

### Requirement: Deterministic TransitionPlan

**Reason**: A plan that does not bind exact operation authority, compensation,
postconditions, and continuation is not a lossless transition model.

**Migration**: Replace every plan compiler and consumer with the single
receipt-bound transition reducer.

## ADDED Requirements

### Requirement: Single receipt-bound transition reducer

ETHOS SHALL reduce one typed operation request, Commitment, fresh Facts, prior
Attestations, and tracked declarations into one deterministic immutable
transition receipt. The reducer SHALL be pure and SHALL own all validation,
authority derivation, effect ordering, compensation, postconditions, and
continuation semantics.

#### Scenario: Identical observations are reduced twice

- **WHEN** the same canonical inputs are reduced more than once
- **THEN** every receipt byte and digest is identical
- **AND** no runtime, command, store, hook, or provider adapter contributes
  hidden lifecycle state

#### Scenario: One authority-bearing fact changes

- **WHEN** the actor, holder, Commitment, Attestation, ref, tree, Lease
  generation, worktree, declaration, or requested effect changes
- **THEN** the receipt identity changes or the reducer blocks

### Requirement: Transition effects are complete or explicitly partial

Terminal success SHALL require post-observation of every declared postcondition.
An externally visible effect without complete postconditions SHALL reduce to a
typed partial result bound to the original receipt and exactly one resumable or
compensating continuation.

#### Scenario: Ref CAS succeeds and Lease projection fails

- **WHEN** a transition advances a ref but cannot advance the exact Lease
  generation
- **THEN** ETHOS either proves exact compensation restored the prestate or
  returns `partial`
- **AND** it SHALL NOT report the operation as applied or done

### Requirement: Semantic persistence is minimal

Only Commitment and Attestation SHALL persist as semantic roots. Facts,
TransitionPlan, Effect, operation authority, Continuation, Lease/controller
views, runtime selection, status, and provider observations SHALL be derived
from current inputs and immutable evidence.

#### Scenario: A derived model is inspected

- **WHEN** architecture tests inspect storage, tracked carriers, and schemas
- **THEN** no derived model owns durable lifecycle progress or reusable authority
- **AND** removing its cache or local projection does not remove repository truth

### Requirement: Dry-run and apply are homomorphic

Dry-run and apply SHALL consume the same reducer and canonical observations.
Apply SHALL accept the exact passing receipt produced by derive and SHALL NOT
recompile a semantically different plan.

#### Scenario: Invocation environment changes after derive

- **WHEN** working directory, `PWD`, `OLDPWD`, process, host, or presentation
  context changes without changing the receipt-bound repository facts
- **THEN** the transition meaning remains identical
- **AND** changed authoritative facts invalidate the receipt before effects
