# Proposal

## Why

The paradigm's tool catalog has no row for sqlfluff. Its carrier is
`.config/checks/sqlfluff/.sqlfluff`: INI is the only form that `--config` reads from a file not
named `pyproject.toml`, and the tool is bound with `--ignore-local-config --config <carrier>`.

- One governed repository carries a dated deviation for it, with the review date 2026-11-28.

## What Changes

- One catalog row for sqlfluff with its carrier and its binding flags.
- The configuration reference names how sqlfluff, ruff and coverage.py resolve the paths of an
  explicit configuration file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The paradigm declaration, its test and the configuration reference. It admits a carrier and adds
no refusal.

Owner: the release lead. Next action: write the row and its test. Read again: at the cut of
0.2.0-beta.12, before the deviation's review date.
