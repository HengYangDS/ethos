## ADDED Requirements

### Requirement: Provider static analysis follows the declared import style

The product Python static provider SHALL apply the import-sorting values that a repository declares in its native Ruff configuration, and Ruff's own defaults where it declares none.

#### Scenario: A repository declares its import style

- **WHEN** a repository's native Ruff configuration declares `force-single-line = true` and its imports follow it
- **THEN** the static evidence does not report `I001` for them
- **AND** an import block that breaks the declared style still blocks with `I001`

#### Scenario: A repository declares no import style

- **WHEN** a repository declares no import-sorting values
- **THEN** the static evidence judges its imports by Ruff's defaults

## RENAMED Requirements

- FROM: `### Requirement: Adopters share applicable quality obligations`
- TO: `### Requirement: Every repository shares the obligations ETHOS owns`

## MODIFIED Requirements

### Requirement: Every repository shares the obligations ETHOS owns

ETHOS SHALL compile every repository's obligations, its own included, as one function of the carriers the repository authors and the values it declares: the shared obligations those facts select, read from the ETHOS product that judges the repository, plus the gates it declares. The same carriers and values SHALL yield the same obligations under any name, profile id, registry path, location or history. A shared obligation SHALL state observable properties and accepted portable limits.

#### Scenario: Binding is not quality qualification

- **WHEN** a valid new or existing repository has no checks for applicable obligations
- **THEN** adoption MAY report its binding effect, but readiness, proof and integration SHALL report the missing obligations rather than quality success
- **AND** an empty native proof floor or a passing command with no relevant evidence SHALL NOT satisfy them

#### Scenario: Native implementations differ but obligations do not

- **WHEN** two repositories use different native tools and layouts for the same applicable property
- **THEN** both are judged against the same scope and evidence contract
- **AND** neither must copy ETHOS's package layout or self-hosted gate commands

#### Scenario: Several native checks cover one property

- **WHEN** an applicable property spans several carrier or tool scopes
- **THEN** fresh admitted reports SHALL jointly cover every applicable subject
- **AND** a gate name, aggregate pass, or one report for only part of that scope SHALL NOT discharge the property
- **AND** shared native execution SHALL be reused rather than repeated for each rule

#### Scenario: Applicability follows repository facts

- **WHEN** a repository contains code, only documentation, or a versioned release target
- **THEN** code correctness, reader navigation, and release-version obligations apply to their respective observed subjects
- **AND** absent, ambiguous or unavailable required discovery is not treated as an empty successful check

#### Scenario: A candidate weakens its own quality policy

- **WHEN** a candidate removes a declared check or narrows its declared source scope
- **THEN** the shared obligations its authored carriers select still judge it, from the ETHOS product that judges it
- **AND** local and hosted consumers reject a result set that omits a required obligation

#### Scenario: ETHOS is judged as every repository is

- **WHEN** ETHOS's tree and another tree author the same carriers and declare the same values
- **THEN** both receive the same shared obligations and the same quality floor
- **AND** changing only the profile id, the registry path, the location or the history changes neither

#### Scenario: The judging product supplies the shared data

- **WHEN** an ETHOS product judges a repository
- **THEN** the shared registry and its provider sources come from that product
- **AND** a tree whose package manifest declares that product's distribution supplies them from its own tree
- **AND** every disposition that dependency acceptance applies is declared by the subject or by the judging product

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

- **WHEN** a candidate changes a CPU reservation, a command or a gate in the registry it declares
- **THEN** its execution policy binds every changed obligation
- **AND** the shared obligations its authored carriers select apply unchanged, whatever its history or registry path

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
