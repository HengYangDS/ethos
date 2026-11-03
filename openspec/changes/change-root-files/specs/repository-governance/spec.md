## ADDED Requirements

### Requirement: Change root files belong to no Change

A file directly in `openspec/changes/`, such as a guide or a template, SHALL belong to no Change.
Prewrite SHALL refuse a selected Change's write as another Change's only for a path inside that
other Change's directory. A selected Change SHALL write a file directly in `openspec/changes/` under
its ordinary material scope and every other prewrite control.

#### Scenario: A selected Change repairs the Change root guide

- **GIVEN** an owned Work Lane with several active Changes, one of them selected
- **WHEN** prewrite requests `openspec/changes/README.md`
- **THEN** it reports no Change path mismatch for that file
- **AND** the selected Change's material scope and every other prewrite control still apply.

#### Scenario: Another Change's files stay refused

- **WHEN** a selected Change's prewrite requests a file inside another active Change's directory
- **THEN** it reports `openspec_change_path_mismatch` for that path.
