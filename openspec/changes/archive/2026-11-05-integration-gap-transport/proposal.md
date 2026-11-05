# Proposal

## Why

The integrated beta-3 proof `ib1` at `ded6a9134` failed one test:
`tests/architecture/test_single_gap_transport.py::test_product_code_never_transports_only_the_first_gap`.
It found `raise ValueError(gaps[0])` in `create_git_commit`
(`src/ethos/adapters/repo/commit/creation.py`).

The two lanes behind it were each correct on their own base:

- `peer-address-boundary` added the whole-message check and raised only its first gap. That was the
  pattern of its base, `be573e25b`.
- `cause-preserving-results`, landed on dev as `a984a18c4`, made every refusal raise all of its
  gaps, and added the architecture test that forbids the old pattern.

The merge combined both, so the product carried one refusal that dropped every gap after the first.

## What Changes

- The commit message refusal in `create_git_commit` raises `refusal(*gaps)`, as the identity refusal
  beside it already does. Its message stays the leading gap, and it carries every gap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement that a refusal reports every gap it found already exists, so
`skip_specs: true` applies.

## Impact

`src/ethos/adapters/repo/commit/creation.py`.
