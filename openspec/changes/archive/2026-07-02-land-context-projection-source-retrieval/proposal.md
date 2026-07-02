## Why

ETHOS assistant context is currently a static projection, so agents still have to
reconstruct relevant source, schema, evidence, and command context by ad hoc file
search. ETHOS needs a source-verified context projection that improves recall
without creating a memory kernel, proof shortcut, or second truth store.

## What Changes

- Add provider-neutral context bundle, selection report, index manifest, and
  policy contracts.
- Add an ignored, rebuildable SQLite/FTS local retrieval index under
  `.ethos/state/retrieval.sqlite`.
- Add source verification for retrieved spans before they can enter assistant
  context bundles.
- Extend assistant context and MCP projections with read-only context/search
  resources and tools.
- Add CLI surfaces under `ethos assistants ...` for context search, index
  lifecycle, purge, and evaluation.
- Add golden and adversarial tests proving context remains advisory and cannot
  satisfy proof or close required gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ethos-contracts`: add context projection schemas and provider-neutral
  contracts.
- `ethos-adapters`: add ignored local source index storage and indexing
  adapters.
- `ethos-repository`: add source verification and quality/proof boundaries for
  context projection.
- `ethos-assistants`: expose source-verified context projection through
  assistant bundles and MCP.
- `ethos-test`: add conformance, golden retrieval, and adversarial fixtures for
  context projection.
- `ethos-cli`: add thin CLI composition for assistant context search and index
  lifecycle commands.

## Impact

- Affected packages: `ethos-contracts`, `ethos-adapters`,
  `ethos-repository`, `ethos-assistants`, `ethos-test`, and `ethos`.
- Affected command surface: new subcommands under `ethos assistants`.
- Affected local state: new ignored `.ethos/state/retrieval.sqlite` cache.
- No new runtime dependencies are required for the MVP.
- No default committed MCP profile or third-party memory adapter is added.
