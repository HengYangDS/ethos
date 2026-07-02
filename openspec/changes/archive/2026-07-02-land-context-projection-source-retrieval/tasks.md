## 1. Governance Carrier

- [x] Create the OpenSpec proposal, design, delta specs, and task list.
- [x] Add `claims/ethos-context-projection-source-retrieval.toml`.
- [x] Add initial dated evidence placeholder for context projection.
- [x] Validate OpenSpec status for the change.

## 2. Contracts And Schemas

- [x] Add context bundle, selection report, index manifest, and policy schemas.
- [x] Add provider-neutral context contract helpers in `ethos-contracts`.
- [x] Add schema validation samples for the new contracts.
- [x] Add focused schema tests and run them red/green.

## 3. Retrieval Local State

- [x] Add `.ethos/state/retrieval.sqlite` initialization in an adapter module.
- [x] Add schema version 1 tables and FTS5 virtual tables.
- [x] Add dry-run/apply index lifecycle reports.
- [x] Add focused local-state tests and run them red/green.

## 4. Source Indexers

- [x] Index Markdown docs by front matter and heading sections.
- [x] Index JSON Schema objects/properties/required fields.
- [x] Index TOML claims and evidence references.
- [x] Index OpenSpec requirements and scenarios.
- [x] Index Python definitions with `ast`.
- [x] Add source indexing tests and run them red/green.

## 5. Source-Verified Retrieval

- [x] Add query intent classification and lexical/symbol retrieval.
- [x] Add deterministic ranking and selection reports.
- [x] Add source-span verification by path, line range, digest, and head.
- [x] Suppress stale or unverified candidates from main context bundles.
- [x] Add retrieval and stale-source tests and run them red/green.

## 6. Assistant Projection And MCP

- [x] Extend `context_bundle()` without breaking static no-query behavior.
- [x] Add context search and diagnostics data to assistant context output.
- [x] Extend MCP manifest resources and read-only tools.
- [x] Add assistant context and MCP tests and run them red/green.

## 7. CLI Composition

- [x] Add `ethos assistants search`.
- [x] Extend `ethos assistants context` with `--scope` and `--query`.
- [x] Add `ethos assistants context-index`.
- [x] Add `ethos assistants context-purge`.
- [x] Add `ethos assistants context-eval`.
- [x] Add CLI contract tests and run them red/green.

## 8. Safety And Evaluation

- [x] Add golden retrieval smoke fixtures under `ethos-test`.
- [x] Add prompt-injection, stale-digest, path traversal, untracked-source,
  secret-like content, and purge cascade tests.
- [x] Add quality/report integration that labels context projection advisory.
- [x] Run focused safety and evaluation tests.

## 9. Docs And Evidence

- [x] Add `docs/architecture/context-projection.md`.
- [x] Update local state, agent projections, MCP server, schema validation,
  command plane, and docs index pages.
- [x] Update claim evidence digest.
- [x] Run OpenSpec, schema, unit, architecture, Ruff, self-audit, and report
  gates.
