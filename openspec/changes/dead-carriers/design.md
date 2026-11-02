# Design

## Context

See [proposal.md](proposal.md). A read-only inventory at `18ed740e0` checked every reader of each
candidate: the three system contracts reach only `system_contracts_report` through the
`product-boundary` gate, which blocks when one is missing, malformed or fails its schema, and the
semantic closure reads only the duplicate-identity issues that `surfaces` produces.

## Goals / Non-Goals

**Goals:**

- Each deleted carrier leaves no reader, test or document that names it.
- `svg` files keep one validation path: the shipped `source-format` provider.

**Non-Goals:**

- Changing a gate field, a shipped schema that has a reader, or any governed repository.
- Deciding the shell policy; the product-shell paradigm rule owns it.

## Decisions

- **Delete rather than bind.** No decision needs the content of the three contracts, so binding a
  reader would create a consumer to justify a carrier.
- **Keep the loader for `surfaces`.** Its identities feed the semantic closure; only the list of
  contracts shrinks.
- **The format policy owns JSONL.** Its `jsonl_allowed_roots` is the only rule that decides where a
  JSONL file may live, so the JSONL format row names that policy as its owner.

## Risks / Trade-offs

- [A document or check still names a deleted file] → The reference closure and the docs gates
  refuse a dangling link, and the tests that listed the files change with them.
