## ADDED Requirements

### Requirement: Exact Node Runtime Compatibility Policy

ETHOS SHALL keep exact npm-launcher compatibility releases in one repository
policy and SHALL execute hosted compatibility acceptance through one reusable
runner rather than provider-inline npm command bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted npm compatibility job runs
- **THEN** `.config/checks/node/runtime.toml` declares Node 24.18.0 and Node
  26.5.0 as the exact compatibility set
- **AND** the provider selects one declared release through `NODE_VERSION`
- **AND** `tools/ci/scripts/run-node-compatibility.sh` rejects an active-runtime
  mismatch before npm executes
- **AND** the runner enables npm engine-strict behavior and executes
  `npm ci --ignore-scripts`, `npm run ethos -- --version`, and
  `npm run test:npm` in that order
- **AND** hosted provider YAML invokes the reusable owner instead of restating
  the acceptance command body

### Requirement: Reviewed Node Default Promotion

ETHOS SHALL keep compatibility expansion separate from hosted packaging-default
promotion and SHALL require a reviewed change for any default transition.

#### Scenario: Compatibility expands without promoting packaging

- **WHEN** Node 26.5.0 is added to hosted compatibility verification
- **THEN** Node 24.18.0 remains the runtime policy default
- **AND** the npm packaging job continues to use the Node 24.18.0 installer
  default
- **AND** Node 26.5.0 is recorded only as the next default candidate
- **AND** 2026-10-28 is an earliest review trigger, not an automatic transition
- **AND** promotion requires current release-status verification, successful
  hosted compatibility results, package evidence, and a separate reviewed
  repository change

### Requirement: Node Runtime Authority Boundary

ETHOS distribution compatibility policy SHALL govern repository proof releases
without claiming mutation authority over separately managed runtime owners.

#### Scenario: Managed runtimes remain outside repository mutation

- **WHEN** workstation, IDE, desktop, application, and hosted Node runtimes are
  inventoried
- **THEN** the repository compatibility policy governs only declared launcher
  proof and hosted projection behavior
- **AND** workstation software supply remains workstation-owned
- **AND** IDE-, desktop-, and application-managed runtimes remain owned by their
  respective applications
- **AND** repository compatibility work does not rewrite those managed runtimes
