# Proposal

## Why

The archived `release-step-coverage` moved the `secrets` session onto `supply_tool`, which
supplies Gitleaks through the repository's own mise. One unit test still replaced the product
materializer instead, so the session called the real supply against the test's fixture repository,
which has no `.config/mise/config.toml`. Proof rp1 failed `unit-architecture` on
`test_history_alone_fails_neither_content_scan`.

## What Changes

- The private-address scan test replaces `supply_tool`, the seam that the session now calls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only a test changes, so `skip_specs: true` applies.

## Impact

`tests/unit/adapters/repo/hook/test_private_address_scan.py`.
