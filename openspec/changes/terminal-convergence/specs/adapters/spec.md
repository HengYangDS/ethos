## ADDED Requirements

### Requirement: Workstation-independent Product Kernel
ETHOS source, schemas, tests, docs, install, lifecycle, and recovery MUST have zero dependency on a workstation-specific control plane.

#### Scenario: ETHOS runs on a clean supported host
- **WHEN** no external workstation-control executable, package, schema,
  environment variable, or endpoint exists
- **THEN** local adoption, status, planning, proof, lane lifecycle, recovery, and installation remain functional

### Requirement: Explicit Adapter Classes
Fact providers, change carriers, gate providers, effect executors, attestation sinks, projections, and scaffolds MUST declare permissions and protocol versions through profiles or manifests.

#### Scenario: An adapter requests an undeclared effect
- **WHEN** its requested path or mutation is outside the manifest permission set
- **THEN** admission blocks before invoking the adapter

### Requirement: No Premature In-process Plugin Framework
Extensions MUST use data or subprocess JSON first and MAY use standard-library entry points only for demonstrated trusted consumers; the core MUST NOT require a DI container, event bus, or pluggy-style framework.

#### Scenario: A single internal implementation requests a plugin layer
- **WHEN** no independent extension consumer exists
- **THEN** the abstraction is rejected and explicit composition remains the terminal implementation

### Requirement: ChangeContract Parsing Fails Closed
Lifecycle MUST parse every reviewed active `contract.toml` even when the current
changed-path set has no material path.

#### Scenario: A malformed contract has no matching material path
- **WHEN** lifecycle review reads the Change
- **THEN** it reports `change_contract_invalid:<change>` rather than treating file existence as validity
