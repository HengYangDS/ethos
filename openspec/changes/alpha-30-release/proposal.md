# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.29` lacks the product Changes that this
lane carries:

- `invocation-scope`: every command observes each immutable Git object and the running build once.
- `inventory-memo-hardening`: the runtime inventory memo trusts only files that the current user
  alone could have written, and a failed save leaves no temporary file.
- `locked-supply-completeness`: ETHOS uses locked supply only when native Mise reports it complete.
  A missing locked npm can no longer resolve to Node's bundled npm. That defect could admit a wrong
  proof, which blocks beta.

## What Changes

- Python supply moves to every release that had been public for at least 24 hours at the move.
  The move runs `uv lock --upgrade --exclude-newer=<move time minus 24 hours>`, then a plain
  `uv lock`, which drops the cutoff option and keeps every resolved version.
- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.30`.
- The `0.2.0-alpha.30` entry is curated from the Unreleased notes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION`, `distributions/npm/package.json`, and the Python locks and floors that
move. If a lock moves, the supply image is rebuilt and bound.
