## Why

Archiving `proof-empty-scope-closure` updated the canonical repository-governance
specification, leaving its source digest in the terminal architecture graph
stale. The actual-source export regression and architecture projection gate
therefore reject HEAD `ecce513d1ff3d96de505131528f2a453477da763`.

## What Changes

- Reconcile the archived empty-scope scenario with the existing proof semantics.
- Refresh only `sources.repository_governance.sha256` in
  `system/projections/terminal-architecture/semantic-graph.json` from the exact
  canonical specification bytes.
- Use existing actual-source and stale-source tests to verify recovery and
  retain rejection of unreconciled sources.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The existing `quality` requirement "Terminal projection export preserves
complete source meaning" already requires this binding. This maintenance Change
sets `skip_specs: true`; it changes neither specification behavior nor the
exporter's validation rules.

## Impact

The implementation scope is exactly
`system/projections/terminal-architecture/semantic-graph.json`, plus this Change's
official artifacts. Canonical specifications, exporter code, historical archive
records, graph semantics and rendering remain unchanged. Verification uses
`tests/unit/projection/test_export_terminal_architecture.py` and the declared
architecture projection gate. Governed proof and integration remain separate
effects requiring fresh admission.
