## Why

ETHOS currently has healthy OpenSpec shape validation and executable proof
plumbing, but the product still permits partial-governance states such as
dry-run proof being reported as proven and OpenSpec records being validated
without a full Claim, Boundary, Evidence, Decision, and Promotion chain.

This change completes ETHOS as a repository-governance product: OpenSpec remains
official-native specification projection, while ETHOS owns trust admission,
execution proof, promotion, archive readiness, and adopter parity as one
verifiable lifecycle.

## What Changes

- Tighten proof semantics so planned gates produce readiness, not proof.
- Add product trust review over active claims, OpenSpec carriers, evidence,
  promotion targets, fallback, and kill signals.
- Extend OpenSpec self-governance from shape validation to lifecycle readiness:
  proposal, design, tasks, delta specs, claim binding, promotion evidence, and
  archive eligibility.
- Bind Work Lane and intake projections to trust-bearing claims without letting
  Backlog/intake state become repository truth.
- Add provider-neutral contracts for capability profiles and trust envelopes.
- Add reusable ETHOS test fixtures for valid and malformed governance lifecycles.
- Preserve reference adopter as a reference adopter profile and parity target without
  hardcoding reference adopter terms into ETHOS core packages.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ethos-repository`: trust admission, proof semantics, promotion readiness,
  OpenSpec lifecycle review, and adopter parity closeout become repository
  lifecycle requirements.
- `ethos-adapters`: official OpenSpec, Work Lane, intake, and provider
  adapters must expose boundary facts without owning product truth.
- `ethos-contracts`: provider-neutral trust envelope, promotion target, and
  capability profile contracts become schema-governed product contracts.
- `ethos-cli`: public proof and self-governance commands must distinguish
  planning, readiness, execution proof, and promotion states.
- `ethos-test`: reusable fixtures must cover complete and malformed governance
  lifecycles for product and adopter repositories.

## Impact

- Affected code: `packages/ethos/src/ethos/cli.py`,
  `packages/ethos-repository/src/ethos_repository/`,
  `packages/ethos-adapters/src/ethos_adapters/`,
  `packages/ethos-contracts/src/ethos_contracts/`, `schemas/ethos/`, and tests.
- Affected docs: governance, architecture, command-plane, OpenSpec
  self-governance, gate runner, capability parity, and evidence records.
- Affected behavior: dry-run proof can no longer claim `proven`; trust-bearing
  closeout requires complete claim, OpenSpec, proof, and promotion evidence.
