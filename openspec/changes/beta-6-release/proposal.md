# Proposal

## Why

beta.6 is the one breaking move planned when beta.5 was split off as a fix release. Adopters and
their kits take two changes at once: result schema 3 with the final `next` vocabulary, and a
publication declaration that carries no peer coordinate and no unexecuted command. The release also
carries every fix landed since beta.5:

- `result-contract`, `result-contract-budget`, `result-contract-coverage` and
  `result-runtime-surfaces`;
- `next-wire-shape`, `peer-resolution` and `profile-problem-keys`;
- `provider-timeout-report`, `hosted-proof-expand` and `bounded-result-readers`;
- `refresh-archive-carry`;
- `fixture-port-neutral`, `test-budget-densify` and `test-budget-margin`.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.6`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.6` entry, completed from the landed Changes. It
  adds:
  - the declaration's retired fields and their repair;
  - local forge resolution;
  - the rollback refusal across a repaired declaration;
  - profile problems and provider timeouts;
  - full reads of bounded results;
  - archive resolution after a refresh.
- The entry names the upgrade paths its journey qualifies: 0.2.0-beta.5, 0.2.0-beta.4, 0.2.0-beta.2
  and 0.2.0-alpha.29. It also names the journeys this beta does not qualify and the known open
  defects.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
