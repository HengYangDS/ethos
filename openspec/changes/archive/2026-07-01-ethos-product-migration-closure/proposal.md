# Proposal: Product Migration Closure

## Summary

Close the ETHOS product migration from historical incubation packages to the
target MECE package ontology, while keeping adopter-specific implementations as
external migration oracles and rollback anchors.

## Motivation

ETHOS had reached a usable governance surface, but the repository still carried
active migration-host packages and some current records described provider
execution, npm launchers, and OpenSpec deltas through old package families.
That weakens product truth, makes future adopters harder to reason about, and
risks reintroducing retired topology during archive or release work.

## Scope

- Retire active migration-host packages from `packages/`.
- Keep npm as `distributions/npm`, not a Python package or second
  implementation.
- Keep `ethos-repository` provider-neutral by moving OpenSpec execution behind
  CLI/adapters composition.
- Require target MECE OpenSpec families and prevent active changes from
  reintroducing old families.
- Keep generic and reference-adopter parity closure evidence tracked while treating
  reference-adopter embedded ETHOS as adopter oracle/fallback, not product truth.
- Validate all Python packages with Hatchling wheel/sdist local build smoke.

## Non-goals

- Do not remote publish.
- Do not delete reference-adopter embedded ETHOS from the adopter repository.
- Do not enter or mutate another agent's Work Lane.
- Do not introduce npm/Homebrew/Docker/CI marketplace publication.

## Capabilities

### Modified Capabilities

- `ethos-contracts`
- `ethos-repository`
- `ethos-cli`
- `ethos-distribution`
- `ethos-test`

## Impact

Affected areas include package topology, dependency boundaries, npm launcher
layout, OpenSpec records, parity evidence, active claims, docs, tests, lock
files, and local build verification.
