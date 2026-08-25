## Why

The terminal architecture currently depends on a sibling directory that owns a
copied semantic graph, copy, view declaration, and quality contract. That makes
the visual projection reproducible, but leaves ETHOS product meaning and the
selected projection assertions under separate tracked owners.

## What Changes

- Move the terminal projection declaration and its lossless selected assertion
  set into ETHOS under `system/projections/terminal-architecture/`.
- Add a deterministic read-only exporter that reads one exact Git tree and
  emits `projection.input/v1` with commit, tree, file digests, coverage
  dispositions, and a content digest.
- Make missing paths, stale digests, incomplete disposition, and any claimed
  effect authority fail closed.
- Keep renderer choice, layout, and delivery outside ETHOS and read-only.

## Capabilities

- `assistant-projections`: subject=terminal-architecture-projection-input;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation;
  facet:surface=system,tool,schema,test,docs;
  facet:authority=source,test,openspec.

## Out Of Scope

- A new public CLI command, daemon, database, workflow engine, renderer, visual
  layout owner, or repository-effect path.
- Automatic owner acceptance, remote publication, accepted-root mutation, or
  deletion of the former architecture directory.
