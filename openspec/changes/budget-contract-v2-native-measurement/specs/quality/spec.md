## ADDED Requirements

### Requirement: Dynamic parser dependency hygiene is explicit

ETHOS SHALL keep a direct parser dependency visible to dependency hygiene when
the provider is loaded lazily to preserve a stable unavailable-provider result.
The declaration SHALL be exact, package-scoped, and justified by the runtime
boundary rather than by a broad unused-dependency waiver.

#### Scenario: Parse-only Jinja remains lazy and dependency-clean

- **WHEN** the Budget Contract v2 Jinja provider is admitted as a direct package
  dependency and loaded only when native measurement selects it
- **THEN** the deptry policy and owner runner SHALL both declare only
  `DEP002=jinja2` for the `ethos` distribution
- **AND** the policy SHALL explain that lazy loading preserves stable provider
  gaps without restoring adoption rendering
- **AND** every other unused or transitive dependency finding SHALL remain
  enforced normally.
