# Design: prune Pixi runtime environments from artifact traversal

## Context

`_candidate_paths()` walks the repository and evaluates generated-artifact
policy. Its `_skip_descendant()` boundary already removes Git metadata, Python
virtual environments, Node modules, and bytecode caches. Pixi creates the same
class of local dependency-runtime tree under `.pixi/`, but it is absent from
that boundary. The walker therefore descends into it; a denied intermediate
directory can then trigger a recursive `rglob()` emptiness check repeatedly.

## Goals / Non-Goals

**Goals:** Keep `ethos quality generated-artifacts` finite and read-only in a
Pixi-backed Work Lane while retaining topology checks outside non-authoritative
runtime trees.

**Non-Goals:** Do not broaden allowed artifact homes, hide tracked source, or
change remote/publication behavior.

## Decisions

Add `.pixi` to the fixed traversal-prune set. This is the smallest correction:
Pixi environments are local dependency runtime, not repository artifact truth,
and the existing `.venv` boundary establishes the same policy.

Alternative: special-case every nested Pixi path. Rejected because the root
walk would still enter the environment and retain the recursive-cost failure.
Alternative: change only the emptiness probe. Rejected because a large local
runtime tree must not be audited as product artifact topology at all.

## Risks / Trade-offs

- [A future repository intentionally tracks `.pixi` content] → its runtime
  tree remains outside generated-artifact topology by the same local-runtime
  boundary as `.venv`; a dedicated contract change is required to make it
  product truth.
- [Adjacent hidden drift is missed] → only the exact `.pixi` root is pruned;
  all other paths still flow through the existing declaration.
