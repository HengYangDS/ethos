# repository-governance Delta

## MODIFIED Requirements

### Requirement: Context-bound mutation admission

ETHOS SHALL bind tracked mutation admission to explicit repository root,
checkout role, editor root, and target paths before a write-capable tool can
mutate tracked files. ETHOS SHALL also reject hidden change carriers that bypass
repository truth surfaces.

#### Scenario: Control-character path token is blocked

- **WHEN** hook or prewrite admission receives a target path token containing an
  ASCII control character
- **THEN** ETHOS blocks the admission with
  `prewrite_path_invalid_control_character`
- **AND** the path report preserves the original token and does not mint a
  repository-relative path claim from it.
