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

#### Scenario: A native capability fails after transport initialization

- **WHEN** a supported application operation cannot resolve a required native executable
- **THEN** CLI, SDK and MCP preserve the same typed blocking reason and root-bound failure evidence
- **AND** restoring that capability allows the same MCP instance to observe again
- **AND** transport adapters do not substitute generic protocol errors for known application failures

#### Scenario: A native Git observation times out

- **WHEN** a supported application operation receives a native Git observation timeout
- **THEN** its result is UNKNOWN with the original process evidence and an observation next action
- **AND** it does not claim a known repository state or authorize mutation replay

#### Scenario: Planning is consumed outside the CLI

- **WHEN** SDK or bound MCP clients request changed-scope or explicitly selected planning
- **THEN** they use the same current intent resolution, authority, gates and continuation as the CLI
- **AND** result composition does not import a CLI handler, write stdout or change the caller working directory

#### Scenario: An operation encounters an invalid-profile failure

- **WHEN** the repository profile owner rejects an operation's configuration
- **THEN** CLI, SDK and MCP retain the same blocking result and recovery guidance
- **AND** a transport does not replace the known failure with a generic protocol error
- **AND** adoption's authored-content conflicts retain their distinct operation-specific meaning

#### Scenario: Integration is consumed outside the CLI

- **WHEN** a bound SDK or MCP caller previews or applies integration
- **THEN** it invokes the same candidate, accepted or release operation as the CLI
- **AND** stale coordinates, missing authorization and required control verification retain their native refusal
- **AND** successful effects retain exact CAS and post-observation evidence without CLI rendering

#### Scenario: A client observes or retries completed accepted closeout

- **WHEN** the accepted and candidate refs, any required release mirror and their
  affected worktrees already satisfy closeout
- **THEN** preview and authorized retry report the same original effect identity
  through the existing Attestation owner, without creating another ref effect
- **AND** aligned bootstrap refs without an effect record remain an unattested
  no-op, not fabricated proof of an earlier transition
- **AND** ambiguous evidence or dirty affected worktrees cannot become successful
  recovery; current authorization and coordinate admission still apply

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

#### Scenario: A native prerequisite prevents MCP startup

- **WHEN** the installed console or module entry cannot establish its native execution boundary
- **THEN** startup exits unsuccessfully without writing diagnostics to protocol stdout
- **AND** stderr preserves the failure and recovery guidance without a traceback
- **AND** the console dispatcher preserves the same native failure evidence as direct invocation

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

## MODIFIED Requirements

### Requirement: Public Command Plane

ETHOS SHALL keep the normal user workflow under six public commands:
`ethos adopt`, `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. Accepted-head admission is an exact `ethos land --closeout`
operation, not a seventh workflow command or a hidden Git-hook procedure.
The additional `ethos mcp --root <repo>` command SHALL launch a protocol transport
over the same application operations without creating lifecycle authority.

#### Scenario: Cyclopts exposes the terminal root surface

- **WHEN** the root CLI help is rendered
- **THEN** it exposes the six workflow commands and the MCP transport launcher
- **AND** `ethos status` is the single bounded reader
- **AND** maintainer mechanics remain hidden or semantically namespaced

#### Scenario: TransitionPlan is the single transition projection

- **WHEN** `ethos plan --json` compiles the current Commitment, repository
  facts, and declared nodes
- **THEN** it returns one deterministic `transition_plan`
- **AND** no parallel workflow-runtime or domain-contract read model is emitted

#### Scenario: Default payloads stay bounded

- **WHEN** `ethos status --json` or `ethos plan --json` would exceed its declared
  default payload budget
- **THEN** the command preserves `verdict`, `state`, `summary`, `required_gaps`,
  `next_action`, `continuation`, `missing_facts_or_evidence`, and
  `user_decision_required`
- **AND** oversized detail is replaced by a digest-bound artifact reference
- **AND** no alternate reader command or truth source is introduced

#### Scenario: a reader derives continuation

- **WHEN** current authoritative facts are sufficient to select the next boundary
- **THEN** the schema-version-`2` result preserves `state` and `required_gaps`,
  exposes one `next_action`, and derives exactly one `continuation`: `continue`,
  `await-user`, `blocked`, or `done`
- **AND** `missing_facts_or_evidence` derives from `required_gaps` only when
  `verdict=unknown`, while `user_decision_required` names required judgment
- **AND** Continuation is recomputed rather than stored as lifecycle truth

#### Scenario: accepted closeout remediation is directly executable

- **WHEN** accepted-head admission is blocked by missing proof, missing external
  verification, stale coordinates, or an unapplied exact effect
- **THEN** status, plan, land, and hook projections SHALL expose the same single
  complete `ethos ...` command
- **AND** that command SHALL bind the current root, expected accepted HEAD,
  candidate HEAD, and any required receipt path
- **AND** it SHALL contain no prose-only instruction or placeholder token.
