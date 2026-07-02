---
subject: ethos:context-projection-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/unit, tests/architecture, OpenSpec, Ruff
---

# Context Projection Evidence - 2026-07-01

## Scope

This evidence records the `land-context-projection-source-retrieval` campaign
slice.

Implemented changes:

- Added provider-neutral context projection contracts in `ethos-contracts`.
- Added JSON Schemas for context bundles, selection reports, index manifests,
  and context policy.
- Added ignored local retrieval state at `.ethos/state/retrieval.sqlite`.
- Added SQLite tables for manifests, source spans, FTS document chunks, Python
  symbols, evidence references, query runs, access audit, and tombstones.
- Added committed-source indexing for Markdown, JSON/TOML governance files,
  schemas, OpenSpec records, package docs, and Python AST symbols.
- Added source-verified retrieval that rechecks repository containment, allowed
  source scope, current HEAD, file digest, and line-span digest before emitting
  a candidate.
- Added stale and unverified candidate suppression for main context bundles.
- Added secret-like content quarantine and redacted query-run persistence.
- Extended assistant context output with nested `context_projection` only when
  a query is supplied, preserving the static no-query bundle.
- Added MCP context resources and read-only retrieval tools.
- Added public commands under `ethos assistants`: `search`, `context-index`,
  `context-purge`, and `context-eval`; no top-level memory/retrieval command
  roots were added.
- Added `ethos-test` golden smoke query fixtures for context retrieval.
- Added `ethos report --json` context projection scoring that labels the
  projection contract as advisory and incapable of proof or gap closure.
- Added context projection architecture, local-state, MCP, schema, and command
  plane documentation.

Review response:

- Four read-only expert reviewers checked governance, security, CLI/MCP
  contracts, and retrieval storage quality.
- Blocking feedback led to path containment checks, HEAD binding, dirty-source
  index blocking, runtime prompt-injection field stripping, schema alignment
  with emitted bundles, canonical `--authorize`, gap propagation from
  `assistants context --query`, non-stub smoke evaluation, symlink quarantine
  before content reads, source-derived result titles, and read-only search
  behavior for MCP tools.
- Final SQLite tamper review led to source-derived result identifiers, so
  verified context no longer emits cache-controlled `id` or `title` metadata.

## Verification

Commands run from the isolated worktree:

```bash
uv run --group dev pytest tests/unit/test_context_schemas.py tests/unit/test_context_index_state.py tests/unit/test_context_retrieval.py tests/unit/test_context_selection.py tests/unit/test_context_cli_contracts.py -q
uv run --group dev pytest tests/unit/test_context_contracts.py tests/unit/test_context_schemas.py tests/unit/test_context_index_state.py tests/unit/test_context_retrieval.py tests/unit/test_context_selection.py tests/unit/test_context_cli_contracts.py -q
uv run --group dev pytest tests/unit/test_agent_context_provider.py tests/unit/test_mcp_server.py tests/unit/test_schema_validation_and_gates.py -q
uv run --group dev ruff check packages/ethos-adapters/src/ethos_adapters/context_index.py packages/ethos-assistants/src/ethos_assistants/context.py packages/ethos-assistants/src/ethos_assistants/context_selection.py packages/ethos-assistants/src/ethos_assistants/mcp.py packages/ethos-test/src/ethos_test/fixtures.py packages/ethos/src/ethos/cli.py tests/unit/test_context_*.py -q
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos self audit --json
uv run --package ethos ethos report --json
uv run openspec validate --type change land-context-projection-source-retrieval --strict
uv run openspec status --change land-context-projection-source-retrieval --json
```

Observed results:

- Initial focused context tests failed before fixes on schema reference
  resolution, stale-hit isolation, and purge dry-run assertions.
- Focused context and contract tests after fixes: `30 passed`.
- Existing assistant, MCP, and schema tests after fixes: `15 passed`.
- Targeted Ruff check after formatting and SQL line wrapping: all checks
  passed.
- Unit and architecture suite: `297 passed`.
- Full Ruff: all checks passed.
- Schema quality: `ok=true`, `schema_count=25`, no required gaps.
- Self audit: `ok=true`, no required gaps.
- Report: `ok=true`, score `16 / 16`, no required gaps.
- OpenSpec strict change validation: change is valid.
- OpenSpec status: planning artifacts are complete.
