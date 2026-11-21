# Proposal

## Why

The paradigm's tool catalog has no row for sqlfluff. Its carrier is
`.config/checks/sqlfluff/.sqlfluff`: INI is the only form that `--config` reads from a file not
named `pyproject.toml`, and the tool is bound with `--ignore-local-config --config <carrier>`.

- One governed repository keeps its sqlfluff policy at `.config/checks/sqlfluff/config.ini` (read
  on 2026-11-22). The paradigm reports that file as a configuration-carrier gap, and no
  declaration of the repository's own closes it.
- The same repository carries names that an upstream contract fixes. The profile's
  `identifier_sources` admits such a name, and the authored-name gap's repair names a rename and
  a `linguist-*` mark only.

## What Changes

- One catalog row for sqlfluff with its carrier.
- The authored-name gap's repair also names the declaration of an identifier source in the
  profile, for a name that an upstream contract fixes.
- The configuration reference names the carrier and its binding flags, and how sqlfluff, Ruff and
  coverage.py resolve the relative paths of an explicit configuration file. The draft
  `configuration-reference-gaps` named the same statement for Ruff and coverage.py; it is
  delivered here and leaves that draft.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The packaged paradigm declaration owns the catalog's rows and no accepted requirement lists
them, so `skip_specs: true` applies.

## Impact

The paradigm declaration, the authored-name reader's repair text, their tests and the
configuration reference. The row admits one carrier and adds no refusal; the repair text changes
no verdict.
