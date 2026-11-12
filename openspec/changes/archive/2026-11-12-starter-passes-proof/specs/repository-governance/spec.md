## ADDED Requirements

### Requirement: Formation passes its own repository paradigm

Formation SHALL compose the `foundation` starter so that its initial commit has no
repository-paradigm gap. It SHALL author the carriers that the paradigm requires and no repair
writes, apply the paradigm's deterministic repairs before the starter's inventory, and refuse before
any effect when the composed candidate still has a gap.

#### Scenario: A foundation project passes the paradigm

- **WHEN** an authorized `foundation` formation plan forms a repository
- **THEN** the repository paradigm reports no gap on its initial commit
- **AND** its toolchain owner exposes the three verbs without selecting a tool.

#### Scenario: The composed candidate has a gap

- **WHEN** the composed `foundation` candidate has a repository-paradigm gap
- **THEN** preview and apply refuse with `formation_starter_paradigm_gap` and name the gaps
- **AND** no target repository or Git ref is created.

#### Scenario: A domain starter has gaps

- **WHEN** the optional Python library starter is selected and its candidate has paradigm gaps
- **THEN** the preview lists them as `paradigm_gaps` without refusing, until that starter conforms.
