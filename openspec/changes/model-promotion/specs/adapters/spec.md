## MODIFIED Requirements

### Requirement: Lifecycle mutation has one semantic owner

All repository lifecycle mutation SHALL execute an immutable transition receipt
derived by the kernel reducer. Git, SQLite, worktree, process, package, OpenSpec,
and provider adapters SHALL implement only the effects and observations named by
that receipt and SHALL NOT infer lifecycle legality independently.

#### Scenario: Adapter receives an effect request

- **WHEN** an adapter is asked to mutate a ref, Lease, worktree, runtime, file,
  process, or provider projection
- **THEN** it requires the exact receipt and effect identity
- **AND** rejects unbound or drifting inputs before mutation

#### Scenario: CLI invokes a lifecycle operation

- **WHEN** a lane lifecycle command resolves its implementation
- **THEN** it calls the common reducer and receipt-bound effect engine directly
- **AND** no compatibility forwarding function, service locator, Runtime graph,
  or command-local lifecycle owner remains

#### Scenario: adapter behavior needs a test seam

- **WHEN** a test replaces one effectful dependency
- **THEN** it patches the owning observation or effect adapter directly
- **AND** production APIs carry immutable values rather than a Runtime object

#### Scenario: retirement reads lease state

- **WHEN** retirement evaluates current Lease coordination
- **THEN** it consumes the canonical typed observation used by the reducer
- **AND** a second SQLite-only lifecycle reader does not remain

## ADDED Requirements

### Requirement: Effect execution is exact and resumable

The common effect engine SHALL re-observe receipt preconditions, execute ordered
effects, post-observe declared postconditions, issue the effect Attestation, and
persist only immutable recovery evidence. Compensation and resume SHALL consume
the same receipt identity.

#### Scenario: Process stops between two effects

- **WHEN** an operation is interrupted after one effect becomes visible
- **THEN** a later invocation reconstructs the state from current observations
  and the immutable receipt
- **AND** chooses only the receipt-declared resume or compensation path

### Requirement: Refresh base is one complete transaction

Refresh-base SHALL bind and converge the work ref, candidate assertion, rebased
head and tree, exact Lease generation and Commitment binding, actor, and
worktree attachment in one transition receipt.

#### Scenario: Refresh reports terminal success

- **WHEN** refresh-base returns `applied`
- **THEN** the ref, Lease, attachment, and Attestation all bind the same new head
- **AND** a fresh prewrite for that lane passes

#### Scenario: Rebase conflicts before ref CAS

- **WHEN** refresh encounters a content conflict
- **THEN** the original branch, head, Lease, and attachment remain authoritative
- **AND** the result carries bounded conflict evidence and one continuation

#### Scenario: Ref CAS succeeds before a later effect fails

- **WHEN** Lease advancement or worktree attachment fails after ref movement
- **THEN** exact compensation restores all prior coordinates when still valid
- **AND** otherwise the command returns a resumable partial receipt

### Requirement: Repository roots ignore hostile process context

Git, OpenSpec, hook, package, and process adapters SHALL execute from the
receipt-bound repository/worktree root with canonical `PWD` and `OLDPWD` rather
than inheriting an unrelated caller context.

#### Scenario: Command is launched from another repository

- **WHEN** an explicit target root identifies the governed worktree
- **THEN** every subprocess observes that root as its repository context
- **AND** no source checkout, adjacent worktree, or caller basename is selected

### Requirement: Archive transitions preserve official diagnostics

Archive derive SHALL run the official OpenSpec read-only semantic precheck.
Apply failures SHALL preserve upstream status code, message, fix, exit code, and
zero/partial file-effect observation in the common result envelope.

#### Scenario: A MODIFIED requirement target is absent

- **WHEN** OpenSpec rejects archive before changing files
- **THEN** dry-run and apply expose `archive_spec_update_failed` and its fix
- **AND** ETHOS does not relabel the adopter delta defect as an internal parser
  failure
