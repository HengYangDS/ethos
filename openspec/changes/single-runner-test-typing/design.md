# Design

## Context

See [proposal.md](proposal.md). The search walks from a Nox session's parsed module to every
function of `tools.ci.sessions`, and of the modules the session imports by name, that a name or
attribute in the walked body references. Both kinds of node are `ast.AST`; only the seed is a
module.

## Goals / Non-Goals

**Goals:**

- The module passes ty with zero violations and the search reaches the same functions.

**Non-Goals:**

- Changing what the test asserts or which sessions it inspects.

## Decisions

- **Annotate the work list rather than cast the seed.** The declared element type states what the
  list holds; a cast would hide the same fact at one call site.

## Risks / Trade-offs

- [The annotation widens the element type] → The loop only walks and inspects nodes, which every
  `ast.AST` supports, so no narrower operation is lost.
