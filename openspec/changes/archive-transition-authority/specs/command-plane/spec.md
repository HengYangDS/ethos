## MODIFIED Requirements

### Requirement: Commitment rebind failures are directly actionable

ETHOS SHALL recognize active Commitment transitions and exact physical archive
relocations as distinct lifecycle conditions and project one typed remediation
rather than a generic ref, bytes, or adoption instruction.

#### Scenario: Normal commit creates a valid dangling target

- **WHEN** hook admission prevents the Work Lane ref from advancing because the
  active Commitment changed but the signed target object was created
- **THEN** ETHOS reports `commitment_rebind_required`
- **AND** it returns the valid target OID, old and new carrier digests, partial
  effects, and the one copy-safe derive command
- **AND** it tells the caller not to repeat the commit.

#### Scenario: Exact archive relocation is not rebound

- **GIVEN** the Lease still names the pre-archive HEAD and active Commitment
  carrier
- **AND** its direct child moves the same Commitment bytes into exactly one
  valid dated archive with only the official archive path set
- **WHEN** Commitment rebind derivation evaluates that child
- **THEN** it reports `archive_transition_requires_archive_change`
- **AND** it does not create a Commitment-rebind receipt
- **AND** it returns the exact `ethos lane archive-change` recovery command.

#### Scenario: Archive-like target is not exact

- **WHEN** a proposed target has the wrong parent, changed Commitment semantics,
  multiple matching archive carriers, or extra non-archive paths
- **THEN** derivation fails closed without selecting an archive recovery target
- **AND** it does not mint a rebind or archive authority.

#### Scenario: Structured remediation remains bounded

- **WHEN** a lifecycle blocker is emitted
- **THEN** its remediation identifies the owner, reason, observed and expected
  values, whether mutation or user decision is required, retryability, and one
  existing public next command
- **AND** full diagnostics remain available through an immutable artifact
  reference rather than an unbounded default payload.

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
  the Change and Lease expected HEAD
- **AND** it does not direct the operator to repository adoption.

#### Scenario: Other stale Lease state remains non-destructive

- **WHEN** proof planning observes Lease staleness that is not an exact archive
  post-image
- **THEN** proof directs the operator to `ethos lane status --json`
- **AND** it does not infer archive recovery or adoption authority.
