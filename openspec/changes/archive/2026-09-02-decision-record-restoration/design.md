## Context

The old `docs/decisions/` tree combined durable rationale with a second
navigation and lifecycle system. Its deletion removed the redundant machinery
but also erased reasons that cannot be reconstructed from current-state docs
alone. Separately, `docs/README.md` and `docs/index.md` both acted as the
documentation entrypoint.

## Goals / Non-Goals

**Goals:**

- Preserve only irreducible context, rejected alternatives, consequences, and
  revisit conditions.
- Keep one documentation entrypoint.
- Keep current meaning and execution authority in existing owners.
- Use physical names that express semantic subjects rather than a document-type
  prefix.

**Non-Goals:**

- No restoration of the former decision grammar or all historical files.
- No decision IDs as runtime identity.
- No generic docs validator added for this repository-specific correction.
- No rewriting of immutable evidence or OpenSpec archives.
- No adopter requirement to reproduce ETHOS's physical docs layout.

## Decisions

### One documentation entrypoint

`docs/README.md` owns both navigation and the explanation of ETHOS's docs
shape. `docs/index.md` is deleted, and active references point to the remaining
owner. Subject-specific directory READMEs remain only where they already own
real navigation or boundary meaning.

### Rationale is selected by meaning, not historical file count

Three lowercase, semantically named records survive: documentation portability,
the proof trust boundary, and source-budget non-compensation. The former
documentation topology records are one decision because they describe one
evolution from fixed physical sameness to portable semantics. Generated-artifact
routing, the declarative compiler, and adopter evidence ownership remain deleted
as Decision Records because their current architecture and policy owners already
carry both behavior and rationale. The former proof-scope compatibility record
is not restored because accepted command and gate owners already carry the
current contract and the compatibility rationale has no remaining independent
consumer.

### Decision records are non-authorizing leaves

Each record links its current owner and contains only the reason for a settled
choice. `docs/README.md` links the records directly. A decisions-local README,
index, template, schema, registry, status taxonomy, or runtime reader would
duplicate an existing owner and is therefore absent.

### History remains history

Current docs and code stop consuming `docs/index.md`. Immutable historical
evidence and archived OpenSpec may still name paths that existed at the time;
their bytes are not rewritten to simulate currentness.

## Migration Plan

1. Remove the decisions-local index and validator additions from the discarded
   draft.
2. Delete `docs/index.md`, move its unique navigation into `docs/README.md`, and
   update all current consumers.
3. Restore three selected rationale records with lowercase semantic filenames.
4. Prove active-reference closure, docs health, formatting, OpenSpec validity,
   and repository gates before the normal archive and exact-CAS lifecycle.
