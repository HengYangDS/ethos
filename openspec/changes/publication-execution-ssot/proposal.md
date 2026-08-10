# Publication execution SSOT

## Why

Declared publication peers are already the accepted topology authority, but
remote proposal publication still lacks a public exact-CAS execution path.
The current read-only command also retains single-peer aliases and validation
fragments that duplicate the declared peer collection.

## What changes

- Compile all declared proposal targets into one immutable `TransitionPlan`.
- Persist the dry-run plan in the existing request store and replay it through
  one exact-CAS executor after rechecking repository and remote coordinates.
- Attest each peer-local result and expose partial effects without claiming
  cross-peer atomicity.
- Remove single-peer aliases, duplicate validation, and ownerless helper
  entities; repeated providers remain valid when peer IDs and Git remotes are
  unique.
- Recalibrate `python_tests` to `36000` while retaining the 95% coverage floor.

## Out of scope

- Forge-specific merge-request APIs or hosted CI success claims.
- A distributed transaction spanning independent Git providers.
- Adopter-specific paths, mandatory providers, compatibility aliases, or a
  second publication state store.

## Affected capabilities

- `repository-governance`: declared peers remain the sole publication topology.
- `command-plane`: proposal publication gains derive, receipt, apply, and
  partial-effect recovery semantics.
- `quality`: the public regression budget is recalibrated without weakening
  coverage or product-source limits.
