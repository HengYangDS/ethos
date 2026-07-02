## Context

ETHOS exposes assistant context today through a static repository-bounded bundle.
That keeps host adapters below repository truth, but it does not help agents find
the exact source, schema, evidence, and command spans needed for a focused task.
The new capability is a read model over repository authority, not a memory
kernel. Chronicle remains the durable judged memory concept.

## Goals / Non-Goals

**Goals:**

- Index allowed repository sources into ignored local state.
- Retrieve candidate source spans through deterministic lexical and symbol
  search.
- Verify candidates against current repository files before use.
- Emit assistant context bundles and MCP resources that stay below repository
  authority.
- Provide a dry-run-first lifecycle for index rebuild, purge, and evaluation.

**Non-Goals:**

- Durable assistant memory outside Chronicle.
- Proof, claim, or required-gap satisfaction from retrieved context.
- Default committed MCP memory profile.
- Vector embeddings, GraphRAG summaries, LSP daemons, or third-party memory
  adapters in the MVP.

## Decisions

### Use Context Projection, Not Memory Kernel

Context projection is a read model over repository truth. A separate memory
kernel would duplicate Chronicle, claims, evidence, and docs. Retrieved context
is always rendered as `UNTRUSTED CONTEXT` and cannot override source, tests,
schemas, docs, claims, or dated evidence.

### Store Retrieval Index In Separate Ignored SQLite

The MVP uses `.ethos/state/retrieval.sqlite` instead of adding high-churn FTS
tables to `.ethos/state/state.sqlite`. The database is local, ignored, deletable,
and rebuildable. It records index manifests, source files, source spans,
document chunks, code symbols, typed edges, evidence refs, query runs, audit
events, and tombstones.

### Keep Package Ownership Split

- `ethos-contracts` owns provider-neutral schemas.
- `ethos-adapters` owns SQLite and source index adapters.
- `ethos-repository` owns source verification and proof/report boundaries.
- `ethos-assistants` owns bundle assembly and MCP projection.
- `ethos-test` owns conformance and evaluation fixtures.
- `ethos` composes CLI output only.

### Start With Lexical And AST Retrieval

The first implementation indexes Markdown, JSON Schema, TOML claims/evidence,
OpenSpec specs, and Python AST definitions. Exact path, symbol, command, schema,
and evidence matches outrank FTS concept matches. Deterministic graph expansion
is one-hop only.

### Verify Source Before Emission

Before a candidate enters the main bundle, ETHOS reopens the current file and
validates line span, content digest, file digest, and repository head binding.
Stale, missing, conflicting, or unsourced candidates are suppressed from the main
bundle and reported in diagnostics.

## Risks / Trade-offs

- Local index truth creep -> keep proof and required-gap checks independent of
  index contents.
- Prompt injection -> label retrieved text as `UNTRUSTED CONTEXT` and reject
  instruction-role fields in schemas.
- Secret leakage -> deny or quarantine secret-like content and keep raw secrets
  out of audit, tombstone, and export records.
- Performance on large repos -> start with bounded FTS and AST indexers, then
  add feature-flagged adapters only after evaluation.
- Command surface churn -> keep all user-facing commands under
  `ethos assistants`.

## Migration Plan

1. Land schemas and contract samples.
2. Add retrieval SQLite initialization and dry-run lifecycle reports.
3. Add source indexers and verification.
4. Extend assistant context bundles and MCP manifest.
5. Add CLI commands and focused tests.
6. Add golden/adversarial fixtures, docs, claim, and evidence.
7. Validate through OpenSpec, schema, unit, architecture, Ruff, self-audit, and
   report gates.
