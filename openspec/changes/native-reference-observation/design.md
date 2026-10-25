# Design

## Context

The native reference-carrier table already distinguishes Python from other syntaxes. Semantic
closure already shares complete trees, but the patch observer independently parses its mixed
context inventory, rediscovers command declarations and reparses selected Python source through
two Python helpers and a second carrier dispatcher. Both public entry points require complete carriers.

## Goals / Non-Goals

**Goals:** classify before parsing, parse each Python carrier once per invocation, and remove
redundant forwarding and fragment-recovery paths while preserving reference reports.

**Non-Goals:** cached Git answers, relaxed admission, new syntax parsers, new entities, changes to
the public command plane, or unqualified adopter controller retirement.

## Decisions

Use the existing carrier table and standard-library AST parser. Compute an invocation-local map
from the exact overlaid input texts, pass it to Cyclopts ownership discovery and the existing
reference dispatcher, and discard it at return. An absent tree remains an unknown observation;
it cannot trigger fragment fallback. Keep native Markdown, YAML and manifest parsers unchanged.

Inline the redundant forwarding and dispatch paths into the existing carrier dispatcher. Both callers
require complete observation, so the private completeness flag and its unreachable fragment
branch retire together. The independent command-declaration parser retains its supported partial
input contract; this change does not globally remove that different operation.

Derive the command vocabulary and selected declarations from the same per-carrier command-owner
observation. A command body is not traversed again merely to project a second view of its owner.

Global caching would weaken freshness and require invalidation machinery. A new inventory object
would add another concept without a consumer. Reusing a previous Git result or parsing every
syntax as Python is therefore rejected in favor of exact, bounded derivation at the current owner.

## Risks / Trade-offs

Context commands must still resolve explicit names and imported application prefixes. Tests bind
mixed carriers, malformed Python, command identity and successive changed input texts. The map
has invocation lifetime only; it is not an authorization or persistent syntax cache.

## Migration Plan

Add distinguishing regressions, simplify the existing observer, run its admission and closure
consumers, then perform native quality checks and exact-current proof. Preserve required failed
evidence and do not land, close out or publish during the existing release hold.
