## MODIFIED Requirements

### Requirement: Proof Command State Semantics

The public result envelope has no top-level `ok` field; `verdict` is the sole
public authorization result.

`ethos prove` SHALL distinguish readiness, exact execution, and recoverable
lifecycle-plan failure while projecting one command owned by the responsible
transition.

#### Scenario: Planning proof is ready

- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `verdict=pass` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven

- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `verdict=pass` and `state=proven`
- **AND** the CLI reports `executed=true`

#### Scenario: Exact committed archive leaves a stale Lease

- **WHEN** proof planning observes a stale Work Lane Lease whose current HEAD is
  the exact recoverable archive post-image
- **THEN** proof blocks with the stale-Lease gap
- **AND** `next_action` is the exact `ethos lane archive-change` command bound to
  the Change and independently observed expected Git HEAD
- **AND** it does not direct the operator to repository adoption.

#### Scenario: Other stale Lease state remains non-destructive

- **WHEN** proof planning observes Lease staleness that is not an exact archive
  post-image
- **THEN** proof directs the operator to `ethos lane status --json`
- **AND** it does not infer archive recovery or adoption authority.

### Requirement: Work Lane writes are exact lease-generation bound

Tracked Work Lane writes SHALL require an active Work Lane lease and an
invocation holder reference matching its exact lane ref, holder ref, positive
generation, and expiry. The mutation request SHALL bind the fresh Work Lane HEAD
as an independent Git fact rather than persisting it in the Lease.

#### Scenario: invocation binding is stale or foreign

- **WHEN** `ethos lane prewrite` runs with a different lane ref, holder ref,
  generation, or expiry than the current Lease, or with a stale independently
  observed Git HEAD
- **THEN** the report blocks the write with the corresponding exact-binding gap
- **AND** visibility of the Work Lane does not authorize write, land, retire, or
  cleanup
