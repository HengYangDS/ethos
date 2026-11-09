# Proposal

## Why

`rules.toml` is an ETHOS binding carrier whose readers consult `[paradigm]`, `[profiles]` and
`[[rule]]`, and read `[artifacts]` and `[quality.code_size]` only to retire them, yet the paradigm
reports no other table in it. A governed repository's `[command_plane]`, `[formats]` and `[gates]`
there are declarations that no reader consults, the class that the workspace binding already removes
from `workspace.toml`; `[artifacts]` already retires into the profile's `record_roots` through the
record binding.

## What Changes

- The paradigm declares the rules binding's tables, `paradigm`, `profiles` and `rule`, beside the
  workspace binding's.
- The paradigm report names every other top-level table of `rules.toml` as a `rules-binding` gap,
  an `[artifacts]` table and a `[quality]` table that still holds `code_size` aside, since their
  own gaps move them; `ethos lane repair-paradigm --apply` deletes each such table, or the file
  when nothing remains, as it deletes an unread workspace table, and a bare top-level value stays
  reported without a repair.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the binding uses only ETHOS-defined files and, in `rules.toml`, only the
  tables its readers consult.

## Impact

- `src/ethos/contracts/paradigm/paradigm.toml` and `declaration.py`, the paradigm report and its
  repair handlers in `src/ethos/repository/paradigm/`.
- Tests of the paradigm report and repair.
- An adopter whose `rules.toml` holds such a table repairs it in its own upgrade Change after the
  release; ETHOS's own `rules.toml` holds only `[profiles]` and `[[rule]]`.
- The deferred repository families keep their bindings until their own migration.
