# Proposal

## Why

`ethos lane repair-paradigm --apply` and the repository profile renderer write TOML through
`tomli_w` with its default four-space indent, while the shipped Taplo policy indents by two spaces.
A repaired `record_roots` array then fails the format check of a repository whose Taplo settings
equal the shipped ones until that repository re-indents it. The 0.2.0-beta.8 entry lists this as a
known open defect, reported by the fleet's adopter session on 2026-11-11.

## What Changes

- One function renders the TOML text of governed files with the indent that the shipped Taplo
  policy's `indent_string` declares. The paradigm repair and the profile renderer use it.
- The 0.2.0-beta.8 entry moves the defect from its known open defects to Fixed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The written values are unchanged; only their layout follows the shipped formatter, so
`skip_specs: true` applies.

## Impact

`src/ethos/repository/toml_layout.py` (new), `src/ethos/repository/paradigm/repair.py`,
`src/ethos/repository/profile.py`, their tests and `CHANGELOG.md`.
