# Design

## Context

An active ETHOS claim is a current proposition with dated evidence, an owner,
a boundary, an OpenSpec carrier, and promotion targets. The prior read model
treated absent `evidence.head` as a migration advisory. All 96 active claims
therefore emitted the same warning, even where their evidence was correctly
dated and digest-bound historical support. Adding the current HEAD to each
record would be less truthful: most historical evidence was not executed at the
current revision.

## Decision

Freshness is a property of the relationship between a claim and its evidence,
not a surrogate claim state.

| Mode | Meaning | Required binding |
| --- | --- | --- |
| `historical` | Dated evidence remains an immutable historical support. It makes no current-HEAD assertion. | No currentness field. |
| `head_bound` | Evidence asserts one exact current repository revision. | `head`. |
| `semantic_scope` | Evidence stays current while its declared promotion semantics are unchanged. | `head` and `semantic_sha256`. |

`semantic_scope` derives its target paths from promotion targets but excludes
the claim file, its dated Chronicle, and archived OpenSpec carriers. Those are
self-describing or historical artifacts; their integrity is already separately
bound by the claim's evidence digest. The remaining tracked tree entries are
hashed at the declared and current revisions.

Missing freshness is a required gap. There is no implicit legacy mode, no
ratchet, and no waiver. Existing delivery claims are migrated explicitly to
`historical`; future currentness-sensitive claims must opt into one of the two
machine-verifiable modes.

## Consequences

- `report` stops presenting durable history as an unfinished migration debt.
- A head-bound claim becomes stale at any different current HEAD.
- A semantic-scope claim becomes stale when a declared semantic target changes,
  but not because an unrelated evidence-recording commit exists.
- A shared semantic-tree digest primitive prevents claims and parity from
  defining incompatible notions of relevant Git state.
