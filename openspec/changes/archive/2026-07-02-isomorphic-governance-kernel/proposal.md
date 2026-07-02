## Why

ETHOS already has self-audit, adopter profiles, OpenSpec carriers, claims, and
proof gates, but the product contract did not make the self-governance and
product-adopter forms a single machine-checked shape. That leaves room for a
half-product state where ETHOS governs itself one way and governs adopters
through another.

## What Changes

- Add a canonical governance profile contract for the `self-governance` and
  `product-adopter` forms.
- Require both forms to share the kernel chain, trust lifecycle, capability
  graph, run steps, truth sources, and advisory projection boundaries.
- Limit differences to authority binding, profile configuration, adapter
  binding, strictness, and rollout policy.
- Validate the contract through `governance-profile.schema.json`,
  `governance_profile_report()`, and `ethos quality schemas`.
- Update product, adoption, schema, and evidence docs so OpenSpec remains a
  carrier while source, tests, schemas, current docs, claims, and evidence own
  promoted truth.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ethos-contracts`: add the provider-neutral governance profile schema
  contract.
- `ethos-repository`: report and validate the isomorphic governance profiles
  through schema validation.
- `ethos-test`: add regression coverage that locks the dual-form product model.

## Impact

Affected areas are `schemas/ethos/`,
`packages/ethos-repository/src/ethos_repository/`, unit and architecture tests,
governance docs, adoption docs, schema docs, OpenSpec records, claims, and
dated local evidence. This change does not publish to a remote and does not
mutate adopter repositories or other Work Lanes.
