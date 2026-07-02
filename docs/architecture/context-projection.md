---
subject: ethos:context-projection
role: reference
state: canonical
relations:
  canonical_for: source-verified assistant retrieval
---

# Context Projection

ETHOS context projection is an assistant retrieval aid over repository truth.
It is not memory truth, proof evidence, workflow authority, or a required-gap
closure mechanism.

The local index lives at `.ethos/state/retrieval.sqlite`. That file is ignored
runtime state and can be deleted and rebuilt. SQLite rows are treated as cache
records only: every returned candidate is re-verified against the current
repository path, current HEAD, allowed source scope, file digest, and line-span
digest before it can appear in a context bundle.

Returned retrieval content is labeled `UNTRUSTED CONTEXT`. Consumers may use it
to choose which repository source to inspect next, but the cited source file,
schema, claim, evidence record, or test remains the authority.

Source policy:

- Index only committed, tracked sources from the allowed repository scope.
- Block apply-mode indexing when allowed tracked sources are dirty.
- Suppress stale candidates when HEAD or digests no longer match.
- Reject tampered paths outside the repository or under ignored state.
- Quarantine secret-like tracked files instead of storing their text in FTS.
- Keep search read-only; the current lifecycle does not persist query-run
  records.
- Emit only a query redaction marker and digest in assistant context bundles;
  raw user query text is not part of the bundle.

Public commands stay under `ethos assistants`:

```bash
ethos assistants context --query "<query>" --json
ethos assistants search "<query>" --json
ethos assistants context-index --apply --authorize --json
ethos assistants context-purge --apply --authorize --json
ethos assistants context-eval --json
```

These commands expose source-verified context projection. They do not introduce
top-level memory, context, or retrieve command roots.

Status: see front matter.

Purpose: explain the source-verified context projection retrieval aid and its
boundary as an advisory read model over repository truth.

See also: [Documentation Index](../index.md),
[Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
