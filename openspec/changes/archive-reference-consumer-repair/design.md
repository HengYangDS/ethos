# Design

## Context

The existing archive adapter repairs links inside moved Change documents and
canonical specs. It does not address a separate authored document that still
links to the removed active Change. The archive is already durable, so replay is
not an option; see [the proposal](proposal.md).

## Goals and Non-Goals

Admit only the current consumer's authored repair. Do not infer a new Change
from history, auto-edit surrounding prose, or broaden the archive effect's
authorized paths.

## Decisions

1. Use the attested archive's exact path set and the current Git tree to
   reconstruct the old-to-archived path relation. Request-scoped, regular,
   tracked Markdown is the only candidate input.
2. Reuse the existing micromark relocation adapter to decide whether a parsed
   destination changes. A filename substring, code fence or explanatory mention
   is not a consumer. The adapter reads Git objects; it does not trust dirty
   working-tree bytes or duplicate Markdown parsing.
3. Project the selected path through the existing OpenSpec material-scope owner.
   Actor, Lease, runtime, patch and native pre-commit checks remain independent.
   The original document owner revises any stale prose. Once committed, a fresh
   read finds no stale link and grants no further repair scope.

This is preferable to automatic destination rewriting: real adopter prose still
called the archived Change “active,” which only its author can judge and repair.
It is also narrower than adding another active Change merely to unblock an
effect that the official lifecycle has already completed.

## Risks and Trade-offs

- A document with another unsupported or broken reference can block this
  derived repair. It then requires an explicit Change rather than a false pass.
- The existing parser does not independently validate URL fragments. The native
  Markdown link gate remains the acceptance check after authored repair.

## Migration

Land and bind the new runtime first. The adopter then obtains fresh exact-path
prewrite, edits its own documents, runs link and proof gates, and commits through
normal hooks. ETHOS does not mutate the adopter or replay its archive.
