## ADDED Requirements

### Requirement: Application operations have transport-independent meaning

CLI, SDK and MCP SHALL invoke the same typed application operations. Transport
adapters SHALL NOT parse CLI output, duplicate verdict rules or own repository
lifecycle state. Requests SHALL bind an explicit repository; results SHALL retain
the existing verdict, gaps, continuation and evidence boundaries.

#### Scenario: One observation is consumed through different transports

- **WHEN** CLI, SDK and MCP observe the same repository facts
- **THEN** their application verdict, gaps and continuation agree
- **AND** SDK invocation does not write stdout or change the process working directory

### Requirement: Installed MCP has bounded repository authority

The installed product SHALL expose stdio MCP through FastMCP over the official SDK. Server
startup SHALL bind its repository and process actor. Tool arguments SHALL NOT
replace that binding or grant authority. Each mutation SHALL retain fresh
existing admission, exact request checks and failure recovery.

#### Scenario: A client attempts a different root or actor

- **WHEN** a tool request supplies undeclared root or actor fields
- **THEN** the request is rejected before application execution
- **AND** the other repository and process actor remain unchanged

#### Scenario: Adoption lacks current authorization

- **WHEN** a client requests adoption without required confirmation or exact HEAD
- **THEN** the shared application returns the existing blocking reasons
- **AND** no adoption binding is written

### Requirement: MCP execution reports its actual effect boundary

MCP SHALL expose discoverable input/output schemas and separate protocol output
from diagnostics. Cancellation or timeout SHALL NOT be reported as completed
cleanup while owned work can still mutate. Unknown results SHALL retain recovery
information rather than trigger an automatic repeated effect.

#### Scenario: A request is cancelled during native work

- **WHEN** a client cancels an executing request
- **THEN** owned execution is drained or its unresolved effect is reported as unknown
- **AND** a retry reobserves the existing effect instead of assuming no mutation occurred

#### Scenario: A real client reconnects

- **WHEN** the official client initializes, discovers tools, calls and reconnects
- **THEN** protocol negotiation and structured results work outside the source checkout
- **AND** repository truth survives without an MCP task database

### Requirement: Adoption continuation preserves request meaning

The shared adoption operation SHALL select one root-bound continuation from the
actual request, binding plan and outcome. Preview SHALL require review before
mutation; conflicts and stale input SHALL NOT appear as applied readiness.
The planner SHALL NOT own a competing public next action.

#### Scenario: Preview or blocked adoption is consumed by another client

- **WHEN** a client receives a preview, conflict or denied adoption result
- **THEN** the result preserves its review or recovery requirement and exact root
- **AND** it does not direct the client to status as though adoption had succeeded

#### Scenario: Adoption succeeds outside the target working directory

- **WHEN** an authorized exact adoption applies successfully
- **THEN** the next observation explicitly selects the adopted repository
- **AND** the caller working directory does not change that selection

### Requirement: Installed context enables portable Agent continuation

Installed CLI, SDK, MCP and Skills SHALL expose coherent product identity,
repository context, applicable capabilities and current continuation. Guidance
SHALL reference native intent and policy owners and preserve authored content.
No specific Agent, model or ETHOS checkout SHALL be required.

#### Scenario: A new client takes over an admitted repository

- **WHEN** a fresh client uses only the installed product and target repository
- **THEN** it can discover intent, constraints, capabilities and the next safe action
- **AND** execute a real admitted change, recover a failure and hand off its result
- **AND** this acceptance is distinct from schema validation or a scripted --help check

### Requirement: Native command declarations are not execution references

Exact patch admission SHALL distinguish adding a native command declaration
from consuming a command. A declaration SHALL remain subject to current
ownership, imports, effects and intent checks. It SHALL NOT grant baseline
authority to execute newly declared commands in the same candidate.

#### Scenario: A transport declares a new command

- **WHEN** an owned Change adds a valid native command using admitted dependencies
- **THEN** declaration alone is not rejected as an undeclared command invocation
- **AND** an unadmitted import or executable in its body remains blocked

#### Scenario: A candidate also consumes the new command

- **WHEN** a patch declares a command and introduces a consumer requiring prior authority
- **THEN** the new declaration does not silently expand the trusted baseline
- **AND** the consumer remains blocked until its declaration is admitted
