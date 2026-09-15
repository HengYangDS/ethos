## ADDED Requirements

### Requirement: Native Hook Execution Loads Only Required Semantics

Native Git hooks SHALL execute their package-owned protocol independently of
interactive CLI dispatch. Notifications and input without a governed effect
SHALL not initialize admission dependencies. Actual admission SHALL use the
existing policy owners and fresh runtime checks, without persistent reuse of
authority. The superseded transport SHALL be removed.

#### Scenario: A native notification has no admission obligation

- **WHEN** a generated hook receives committed, aborted or unrelated ref input
- **THEN** it completes without initializing the CLI or admission machinery.

#### Scenario: A native protocol envelope is malformed

- **WHEN** native hook input cannot be parsed as its expected protocol
- **THEN** the invocation fails without treating absent admission as permission.

#### Scenario: A prepared batch requires admission

- **WHEN** the hook receives one or more governed prepared updates
- **THEN** it fully validates the current runtime once before applying existing policy to each update.

#### Scenario: Prepared authority is damaged

- **WHEN** the selected runtime or required admission dependency is unavailable
- **THEN** the native hook rejects the update rather than using a notification fast path.
