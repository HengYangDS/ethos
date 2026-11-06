# Proposal

## Why

The hosted `external link health` job failed on GitHub runs 42191449672 and 42237913428, although
lychee finds no broken link. The `external-links` gate fails when lychee writes to stderr, and lychee writes a hint for
the one link that redirects: `docs/research/foundations/interfaces.md` links FastMCP's tool
documentation at an address that now answers with a permanent redirect (308) to its new location.

## What Changes

- The link names the address that the redirect resolves to.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `docs/research/foundations/interfaces.md`.
