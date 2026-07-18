# adapters Delta

## MODIFIED Requirements

### Requirement: Prewrite Admission

ETHOS SHALL gate tracked writes through the current Work Lane role and editor
root binding before files are edited.

#### Scenario: Path token contains a control character

- **WHEN** `ethos lane prewrite` or hook admission checks a target path token
  containing an ASCII control character
- **THEN** ETHOS returns a blocked path report with reason
  `path_invalid_control_character`
- **AND** the top-level prewrite error is
  `prewrite_path_invalid_control_character`.
