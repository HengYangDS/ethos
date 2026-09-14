## Why

Repeated native Git subprocesses and repeated decoding of unchanged Attestation
bytes make proof, lane transitions and publication scale with accumulated history.
The existing set owner must reduce that work without reusing authority decisions.

## What Changes

- Batch canonical blob insertion and isolated-index construction through native
  Git, preserving exact parentless set roots, modes and content.
- Reuse only successful pure validation of identical bytes in bounded
  process-local memory. Reobserve selected refs and raw objects on every read.
- Keep changed bytes, missing objects, malformed framing, invalid members and
  stale CAS observable; cache eviction changes cost, never the verdict.
- Remove per-member Git process creation and verify native consumer behavior.

## Capabilities

### Modified Capabilities

- `adapters`: subject=attestation-materialization; reuse=extend; change=modify

## Impact

The existing Attestation set owner and its real-Git tests change. Public readers,
proof admission and publication consume the same interface. No dependency,
persistent cache, permission store, new command or adopter carrier is added.

## Out Of Scope

- Fixture startup deadlines and remote availability classification.
- Historical identity replacement and tag admission diagnostics.
- Whole-proof reuse, hosted runner scheduling and unrelated projection redesign.
