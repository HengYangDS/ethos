## Context

`system/gates.toml` already owns executable gates and proof floors. The former
`system/tools.toml` repeated tool, configuration, executable, artifact, and
profile facts, while `src/ethos/quality` projected more structures from those
same declarations. None was an independent decision surface.

## Goals / Non-Goals

**Goals:**

- leave one gate graph and one positive owner for each retained reference;
- preserve current proof behavior while deleting duplicate declarations;
- make repository semantic closure follow only selected, current carriers.

**Non-Goals:**

- no new quality framework, registry, compatibility reader, or migration table;
- no expansion of the quality floor, thresholds, CI matrix, or proof protocol;
- no rewrite of immutable historical evidence that names retired paths.

## Decisions

### The gate graph has no registry dimension

Every declared gate belongs to the one graph. Proof sets select dependency
closures directly; callers no longer select a `runtime` or `quality` view.
Unknown legacy fields fail through the strict existing contract.

### Existing native owners absorb the unique surviving facts

`system/surfaces.toml` owns host executables and runtime inputs. Native supply
policy owns downloaded tool identity. `system/gates.toml` and provider policy
select scripts; semantic closure follows only those scripts and their explicit
transitive script calls. Unselected scripts do not gain authority merely by
existing under a scanned directory.

### Duplicate projections are deleted

The tools contract/schema, Python quality package, and quality projection
schemas leave together with their consumers. Tests assert absence and strict
rejection instead of preserving readers or aliases.

## Migration Plan

1. Remove the registry field from gate contracts, profiles, fixtures, and gate
   declarations.
2. Move retained executable and runtime-input ownership to existing native
   carriers.
3. Delete the tool catalog, quality package, projection schemas, and consumers.
4. Synchronize docs and skills, validate semantic closure, and run the affected
   quality and OpenSpec gates before lifecycle closeout.

## Risks / Trade-offs

- A hidden consumer may still name a retired path; repository-wide reference
  closure and affected tests must expose it before proof.
- Script discovery could over-admit unrelated files; traversal therefore starts
  only from scripts selected by a gate or provider declaration.
- Historical evidence retains old names as inert history and is not rewritten.
