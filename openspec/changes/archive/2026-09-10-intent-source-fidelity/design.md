## Context

The accepted `compile_intent_context` rereads selected files separately for
requirements, scenarios, non-goals and questions. Its literal list matching
loses valid CommonMark forms, and `_paths` discards missing or escaping sources.
Existing tests provide an artificial spec-only context and do not test the
source-to-projection boundary. The September 10 research supplies the concrete
counterexample: allowing all alternatives to be dropped is not requiring one
winner, and declining integration is not authorizing destruction.

## Goals / Non-Goals

Goals: conserve complete selected source; expose exact observation failures;
extract useful structure with native syntax; preserve zero/one competing and
multiple cooperating results as distinct valid outcomes; separate evidence
claims and make the next Agent's source review explicit.

Non-goals: another interpretation database, a universal semantic oracle, new
execution state, a persistent graph or retrospective certification of research.

## Decisions

1. Official OpenSpec still selects documents and compiles acceptance. Its
   selected context is read once per unique normalized repository path. Each
   transient source entry carries path, exact UTF-8 content and SHA-256.
   Invalid path declarations, missing/unreadable documents and escapes produce
   exact gaps, never an apparently complete empty projection.
2. The already-admitted markdown-it CommonMark parser owns Markdown syntax.
   Its heading and block tokens supply summaries; fences do not create headings,
   wrapped paragraphs stay together and a peer heading closes a section.
   Full source remains available when a summary has no recognized heading.
3. The context identifies interpretation as not assessed by this structural
   compiler. Preserved source, valid structure, accepted meaning, sufficient
   checks, performed effects and achieved user goals remain different claims.
   Duplicate titles are a structural diagnostic, not proof of semantic conflict.
   Preserve the official artifact rows directly instead of separate dependency
   and completion collectors; no consumer needs that duplicate representation.
4. Repository guidance requires an Agent to account for every relevant source
   constraint as retained, explicitly excluded by an authorized decision, or
   unresolved. Wrong interpretations are challenged using positive and negative
   examples against the original source, not their own generated tests. The
   accepted result remains in official proposal/design/specs/tasks.
5. The existing product contract describes the complete engineering and usage
   chain with a small trust kernel and replaceable specialist capabilities. The
   existing plan integrates the research phases and unproved workloads without
   creating another roadmap or declaring this step the whole P1 acceptance.

## Risks / Trade-offs

Full source increases a transient response's size. It replaces repeated reads
and avoids source loss; consumers may request narrower official context but
must not present an omitted source as fully reviewed. Actual semantics still
require an accepted interpretation and appropriate verification; a digest proves
identity, not understanding. No authority is granted by an advisory projection.

## Migration Plan

Replace the old extraction implementation in its existing owner and update its
consumers/tests directly. Keep native OpenSpec artifacts and existing transient
Commitment identity unchanged. No compatibility collector or new store remains.
After focused counterexamples, run affected gates and exact proof, then use the
public archive/acceptance/runtime path. The complete all-drop trace follows in
subsequent bounded work with this source contract as its prerequisite.
