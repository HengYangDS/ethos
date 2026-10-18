## MODIFIED Requirements

### Requirement: Resource coordination preserves complete proof

Gate execution SHALL compose dependencies with declared shared and exclusive
resource-domain claims. Unknown access SHALL retain conservative coordination.
Resource claims SHALL NOT grant mutation authority or assert filesystem sandboxing.
Positive per-gate CPU reservations SHALL bound concurrent work against the
executor's observed capacity; they are scheduling claims, not CPU affinity.

#### Scenario: Independent required checks overlap

- **WHEN** selected source readiness passes and ready gates have compatible resource claims
- **THEN** the shared executor may run them concurrently within its capacity
- **AND** exact artifact consumers still wait for their producer
- **AND** results remain in canonical plan order without duplicate execution

#### Scenario: A writer conflicts with an active consumer

- **WHEN** exclusive access overlaps an active resource or its ancestor domain
- **THEN** those gates do not overlap
- **AND** an unspecified writer retains global exclusion
- **AND** a waiting writer does not prevent other compatible ready work from progressing

#### Scenario: Low-capacity hosts do not co-schedule heavy checks

- **WHEN** two otherwise compatible gates each reserve two units
- **THEN** they run once without overlap at capacity three
- **AND** they may overlap at capacity four when dependencies and locks permit
- **AND** one gate whose reservation exceeds capacity still runs alone

#### Scenario: Scheduling capacity does not redefine quality ownership

- **WHEN** a candidate whose history the running build shares changes a CPU reservation, a command or a gate in `system/gates.toml`
- **THEN** the predecessor and candidate keep the product registry owner without comparing bytes with an installed copy
- **AND** the candidate's execution policy still binds every changed obligation
- **AND** a repository without that history receives the adopter quality floor, even for a verbatim copy of the product registry

#### Scenario: Source proof disagrees with the installed ref guard

- **WHEN** a candidate proof passes but the selected installed runtime cannot compile the same exact policy
- **THEN** read-only landing reports the predecessor's gap before a ref intent or CAS
- **AND** the effect-time Git hook still rechecks fresh state independently

#### Scenario: Construction does not establish quality acceptance

- **WHEN** a package check succeeds but a required test or coverage check fails
- **THEN** complete proof remains blocked
- **AND** construction need not wait for unrelated test output it does not consume
- **AND** every selected source preflight and final proof obligation remains required

#### Scenario: Native resource claims require bounded qualification

- **WHEN** a gate declares complete resource coordination domains
- **THEN** its native owner accounts for source, outputs, scratch and shared supply
- **AND** the declaration is bound into proof policy and checked with overlap and conflict cases
- **AND** the real combined workload verifies artifact identities, source stability and cleanup
- **AND** invocation-local coordination does not replace native cross-process locks or fresh effect admission
