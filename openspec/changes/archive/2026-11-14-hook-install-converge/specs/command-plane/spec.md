## MODIFIED Requirements

### Requirement: Hook installation reports repository-family convergence

`ethos hook install` SHALL project one Git-common activation operation rather than only the
invoking worktree. No installation result SHALL name, as its next step, the operation, root and
request that produced it: a converged installation SHALL continue to the repository's own next
step, and a refused one to another request or to `ethos status`.

#### Scenario: Installation converges linked worktrees

- **WHEN** hook installation succeeds from any linked worktree
- **THEN** JSON reports the effective common hooks path and immutable runtime identity
- **AND** it lists every linked worktree as checked or repaired
- **AND** it lists exact checked, removed, and retained generated paths
- **AND** `next_action` is empty because no further repair is required.

#### Scenario: Installation cannot establish convergence

- **WHEN** a linked worktree or generation consumer cannot be observed exactly
- **THEN** installation returns a non-pass verdict before deleting a generated path
- **AND** `next_action` is the complete root-bound `ethos status` command, whose hook-runtime
  inspection names the repair.

#### Scenario: Activation holds while reclamation is deferred

- **WHEN** the runtime, hooks and state are activated and reclamation cannot finish
- **THEN** the result keeps the activation observation and the gap `hook_runtime_cleanup_deferred`
- **AND** `next_action` is the complete root-bound `ethos status` command, never the installation
- **AND** the status that follows asks for no installation while the runtime stays current.

#### Scenario: Only a state reset repairs the refusal

- **WHEN** an installation that is not an authorized reset refuses for state that only a reset
  repairs
- **THEN** `next_action` is the root-bound `ethos hook install --reset-state --authorize` command.
