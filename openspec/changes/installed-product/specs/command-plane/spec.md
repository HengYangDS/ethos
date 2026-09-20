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

The installed product SHALL expose stdio MCP through the official SDK. Server
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
