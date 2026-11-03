# Proposal

## Why

The full proof of the lane's head after `mise-tool-import` stopped at the `unit-architecture` gate:
`test_product_code_restates_no_declared_value_and_tools_only_shed_theirs` counted 20 string
constants under `tools/` that restate a value the repository paradigm declares, against a ratchet of
19 that only falls. `release-journey` added one: the journey reads `CHANGELOG.md` by its literal
name instead of the paradigm's declared changelog. The fixture's trust registry, which the same
Change moved into `declare_trust_registry`, also names the profile as `.ethos/profile.toml` twice.

## What Changes

- The journey reads the changelog that the paradigm declares for releases.
- `declare_trust_registry` takes the profile path from the paradigm's binding.
- The tools ratchet falls from 19 to 17 restatements.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The paradigm requirement already owns these names, so `skip_specs: true` applies.

## Impact

`tools/ci/delivery/acceptance/journey.py`, `tools/ci/delivery/acceptance/adopter.py` and the
owned-literals architecture test. No behavior or release entry changes.
