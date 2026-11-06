# Proposal

## Why

The archived `release-node-declaration` hashes the shipped Node executable with
`hashlib.file_digest` over the stream that `tarfile` returns. Ty refuses that call: the stream's
declared type `IO[bytes]` matches neither of the function's overloads, so the repository's
zero-tolerance type gate would fail the proof.

## What Changes

- `shipped_node` in `tools/ci/release_supply_chain.py` hashes the stream in fixed-size chunks with
  `hashlib.sha256`. The digest and the behavior are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The digest is the same, so no requirement changes and `skip_specs: true` applies.

## Impact

`tools/ci/release_supply_chain.py`. The existing archive-reading test covers the result.
