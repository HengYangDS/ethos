## ADDED Requirements

### Requirement: Local dependency runtime trees are excluded from artifact topology traversal

ETHOS SHALL exclude non-authoritative local dependency runtime roots from
recursive generated-artifact candidate traversal, including a Pixi `.pixi/`
environment tree, while retaining generated-artifact policy evaluation for all
non-excluded repository paths.

#### Scenario: Pixi-backed Work Lane runs the topology gate

- **WHEN** `ethos quality generated-artifacts --json` runs in a Work Lane that
  contains a local `.pixi/` environment tree
- **THEN** the audit SHALL prune `.pixi/` before recursive candidate descent
- **AND** the command SHALL remain finite and read-only
- **AND** adjacent non-excluded generated-artifact drift SHALL remain subject to
  the existing policy.
