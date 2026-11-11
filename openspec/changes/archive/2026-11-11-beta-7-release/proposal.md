# Proposal

## Why

beta.7 ships what dev has gained since beta.6: the operation catalog for every command, gate
policies that fail closed, stricter Ruff and ty, a commit-range proof, decision density and the
parallel-implementation gate over tests, supply moves to the current images, and the record
retirement and peer-identity work. Adopters have taken nothing since beta.6, and the catalog's
Breaking lines change how their kits call `lane`, `hook`, `attestation` and `host run`, so the
release names each break with its one repair.

## What Changes

- `VERSION` moves to `0.2.0-beta.7`, with any other carrier that `release-identity-check` names.
- The `[Unreleased]` entry becomes the `0.2.0-beta.7` entry, completed from the landed Changes and
  the release build's audit. It names the upgrade paths its journey qualifies, the journeys this
  beta does not qualify, every advisory the audit reports, and the known open defects a user can
  meet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md` and `VERSION`.
