## ADDED Requirements

### Requirement: Start Change accepts explicit predecessor identities

`ethos lane start-change` SHALL accept repeatable predecessor Commitment digests
and SHALL add the current Lease-bound Commitment digest mandatorily. The public
request, dry-run, apply, recovery, and result SHALL refer to the same complete
canonical predecessor set.

#### Scenario: One successor joins several predecessors

- **GIVEN** the current owned Work Lane Commitment and additional historical
  Commitments resolve in the exact base Git tree
- **WHEN** the caller repeats `--predecessor <digest>` during `start-change`
- **THEN** the new Commitment contains the current digest and every additional
  digest exactly once in canonical order
- **AND** the public result identifies that same predecessor set

#### Scenario: Caller repeats or includes the current predecessor

- **WHEN** explicit predecessor input contains a duplicate or the current
  Lease-bound Commitment digest
- **THEN** the command rejects the ambiguous request before mutation
- **AND** it identifies the exact duplicate or redeclared-current-predecessor
  defect without silently normalizing caller input
