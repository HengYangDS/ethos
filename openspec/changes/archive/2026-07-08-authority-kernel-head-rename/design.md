# Design: Authority Kernel Head Rename

## Context

The official OpenSpec boundary is the current `kernel` capability and
`repository-governance` capability. The repository product boundary is the
single ETHOS kernel chain and the protected-root mutation discipline.

## Design

`Authority` is the kernel head. It owns only the authority order reference,
derived views, and policy references; downstream lifecycle, evidence, claim, and
chronicle duties remain outside it. Current truth surfaces use `Authority` in
code, JSON schema, docs, authority graph, invalid-state taxonomy, and tests.
Historical evidence and archived OpenSpec records are not rewritten merely to
match current vocabulary; they remain chronicle/history.

Protected-root projection pollution is treated as substrate untrusted state:
accepted roots must not contain host plans or scratch decomposition paths. Such
material is either absorbed into an owned Work Lane with evidence or reverted
from the protected root after classification.

Lease reads use a read-only immutable SQLite URI fallback when the default local
connection fails, so Work Lane visibility degrades toward observation rather
than disappearing.

## Alternatives

- Keeping the superseded predecessor vocabulary preserves compatibility but keeps
  a long name as a semantic center. This conflicts with parsimony and the
  user's explicit naming concern.
- Leaving tracked historical vocabulary unnormalized makes grep results noisy and weakens the
  truth/history distinction.
- Allowing `.ethos/decomp-recipes` in accepted roots would turn scratch planning
  into product truth.

## Proof Strategy

- Focused tests for kernel contracts, invalid-state taxonomy, authority graph,
  validation gates, lane state fallback, and product design contract.
- Claims and OpenSpec lifecycle audits.
- Head-bound `ethos prove --execute` before land.
