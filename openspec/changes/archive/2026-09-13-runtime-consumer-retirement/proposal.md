## Why

Runtime retirement currently treats any historical text containing a generation
path as a live dependency. Five obsolete generations remain pinned by old
diagnostic receipts even though the current operation contracts do not consume
those runtimes. Cleanup also reuses a pre-activation consumer snapshot.

## What Changes

- **BREAKING** Define runtime retention by operational dependencies: the selected
  generation, effective configuration and current native execution references.
  Historical observations retain provenance, not installed executable lifetime.
- Move generation retirement into the existing runtime package as its sole
  lifecycle owner; remove generic scanning of operation and transaction text.
- Recheck current dependencies under the selector fence immediately before each
  destructive effect. Preserve newly referenced resources and report unavailable
  observations without claiming cleanup success.
- Keep successful activation distinct from deferred reclamation. A diagnostic
  record cannot veto a valid install or create another runtime authority.
- Prove bounded repeated cleanup, active-consumer preservation, fresh-coordinate
  checks and precise partial outcomes through the public installation boundary.

## Capabilities

### Modified Capabilities

- `repository-governance`: operationally justified generation retention and
  post-activation, freshly admitted reclamation.
- `runtime-activation`: distinguish activation rollback from deferred
  post-activation reclamation without weakening either boundary.

## Impact

The existing hook activation, runtime selection/retirement, their tests,
runtime-state documentation, canonical terminal plan and source-bound diagram
bindings. No new dependency, persistent consumer registry, task database,
adopter-specific rule or general transaction framework.

## Non-Goals

This Change does not redesign temporary-test scavenging, eliminate all proof
latency, upgrade the supply chain, or claim isolation from an uncooperative
same-UID writer. Fresh observation is a bounded admission check, not an atomic
lock on every operating-system process or arbitrary external Git configuration.
