# Proposal

## Why

The protected-peer feed promises the hosts, ports and namespace paths of a peer's fetch and push
URLs and of `forgeRepository`, but it fed `forgeRepository` only as a path, and the whole value at
that, so its host and port never reached the feed. On 2026-11-11 an adopter's redaction refused a
forge web address on its own port as unclassified: the feed held the host from the SSH URL but not
the web port from `forgeRepository`, so the scan could not classify the span.

## What Changes

- `feed_from_config` reads each `forgeRepository` value with `remote_parts`, as it reads fetch and
  push URLs, so its host, port and namespace path join the feed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The feed now does what its owner's documentation and the paradigm's peer identity rule
already state, so `skip_specs: true` applies.

## Impact

`src/ethos/adapters/repo/peer_feed.py`, `tests/unit/adapters/repo/test_peer_feed.py` and
`CHANGELOG.md`.
