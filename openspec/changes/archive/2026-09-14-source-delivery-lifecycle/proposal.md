## Why

ETHOS currently requires an official Change to be archived before source can
reach candidate, accepted or release refs. A Change that includes actual
delivery cannot complete those tasks before integration. The result is a
dependency cycle, not incomplete adopter documentation.

## What Changes

- **BREAKING**: distinguish exact source acceptance from whole-Change completion.
  An active official Change can accompany accepted source and remain the sole
  progress carrier through delivery.
- Select repository-transition proof by its exact source, intent, policy and
  evidence, rather than requiring archive as a proxy for acceptance.
- Remove repeated active-carrier prohibitions from source/ref admission,
  publication and lifecycle readers. Preserve current authority and exact CAS.
- Keep incomplete tasks visible and keep archive conditional on completed
  obligations. Update the existing contract and skill projections.
- Keep declared source-binding projections consistent within the exact archive
  effect, without granting general post-archive write authority.

## Capabilities

### Modified Capabilities

- `adapters`: subject=official-lifecycle; reuse=extend; change=modify
- `repository-governance`: subject=source-acceptance; reuse=extend; change=modify

## Impact

The existing OpenSpec observer, proof selector, candidate/accepted admission,
publication and command readers change together. No dependency, persistent
state store, adopter carrier or separate delivery ledger is introduced.

## Out Of Scope

- General post-archive repair admission and malformed canonical-spec recovery.
- Expired Lease recovery commands and lane-start positional parsing.
- General proof caching, supply upgrades and architecture quality-contract debt.
- Changes to external adopter, host-control or diagram repositories.
