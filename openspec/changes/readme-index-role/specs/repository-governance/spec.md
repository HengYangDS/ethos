## ADDED Requirements

### Requirement: A directory README is its index

Every README.md that the docs registry admits SHALL declare `role: index` and hold its directory's
purpose, scope and navigation to its children in at most 100 nonblank lines; policy, procedure,
evidence and history SHALL live on named pages. Docs health SHALL report
`docs_readme_not_index:<path>` and `docs_index_too_long:<path>:<lines>>100`, neither with an
automatic repair.

#### Scenario: A README carries policy

- **WHEN** a registered README.md declares `role: policy`
- **THEN** docs health reports `docs_readme_not_index:<path>`

#### Scenario: An index outgrows navigation

- **WHEN** a registered README.md declares `role: index` and holds 101 nonblank lines
- **THEN** docs health reports `docs_index_too_long:<path>:101>100`

#### Scenario: A short index passes

- **WHEN** a registered README.md declares `role: index`, routes to its children and holds at most
  100 nonblank lines
- **THEN** docs health reports no README role or length gap
