## Context

Official OpenSpec has two valid intent shapes: Changes with requirement deltas,
and Changes that explicitly declare `skip_specs: true` because they alter
release, tooling, documentation, or supply-chain state without changing product
requirements. ETHOS already treats official OpenSpec as the sole tracked intent
carrier, but its Commitment compiler currently requires a non-empty `deltas`
array. That local assumption contradicts the official lifecycle and creates a
prove/archive deadlock.

## Goals / Non-Goals

**Goals:**

- Accept an official, completed, explicitly spec-free Change without fake spec
  deltas.
- Compile a deterministic and non-empty transient Commitment from official
  projection fields only.
- Fail closed for an empty-delta Change that did not explicitly opt into the
  official spec-free lifecycle or lacks its required artifacts.
- Preserve acceptance identity through the existing attested archive effect.

**Non-Goals:**

- No new carrier, metadata schema, registry, compatibility layer, or archive
  database.
- No change to Lease, lane retirement, CLI grammar, runtime migration, version
  identity, publication, or tempfile ownership in this atom.
- No parsing of prose from repository files outside the official OpenSpec
  projection.

## Decisions

### Extend the existing compiler instead of adding a second path

`commitment_from_projection()` remains the sole compiler. Deltas with official
requirements keep their current requirement/scenario acceptance. A projection
without requirements is admitted only when official `status` marks the specs
artifact `skipped`, every required artifact complete, and official apply
instructions report `all_done`.

The spec-free acceptance is a canonical tuple over those official projection
facts and SHA-256 identities of the official metadata, proposal, design, and
tasks bytes. It does not parse arbitrary proposal prose, predict file scope, or
create another lifecycle state.

### Validate positive facts, not exceptions

The compiler does not maintain a list of release/tooling/docs exceptions. It
checks one official positive declaration and the official completion facts.
Missing declaration, missing artifact, malformed projection, or unexpected
delta shape remains `openspec_acceptance_missing` or
`openspec_show_invalid`.

### Reuse archive-effect authority

Archive currentness remains owned by the verified archive-effect Attestation
and Git ancestry. The same transient Commitment digest compiled before archive
is stored in that effect and resolved after archive; archived directories are
not scanned as an active database.

## Risks / Trade-offs

- **OpenSpec JSON field spelling may change** → bind the regression to the real
  repository-locked CLI projection and keep parsing at the existing adapter
  boundary.
- **Artifact presence alone could admit incomplete tasks** → require the
  official projection's completed lifecycle state rather than reading files
  ad hoc.
- **Acceptance may accidentally depend on prose formatting** → bind only stable
  official identities and completion facts, not full artifact text.

## Migration Plan

1. Capture a real valid `skip_specs: true` projection from the locked OpenSpec
   CLI and add a failing compiler regression.
2. Extend the existing compiler with the minimum positive spec-free branch and
   keep malformed zero-delta projections failing closed.
3. Run focused compiler and archive/currentness tests, then affected quality
   gates.
4. Prove the exact implementation before archive, archive through the official
   transition, and prove currentness again from the durable archive effect.
