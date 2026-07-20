## Why

ETHOS already classifies product bindings, mandatory governance dependencies,
native protocols, product toolchains, adapter/profile bindings, evidence, and
fixtures. The remaining gap is admission: a new external framework can look
neutral while still entering the registry without an explicit authority,
boundary, or decision state. That weakens the single-kernel rule and lets a
provider surface approach repository truth by omission.

## What Changes

- Require each `profile_or_adapter_binding` in the coupling registry to expose
  admission authority, truth boundary, and decision state.
- Schema-govern that admission object so command JSON cannot drift from the
  implementation.
- Keep provider names out of the product ontology; the rule hardens the generic
  boundary instead of adding a vendor-specific ban list.
- Add regression tests for missing, wrong-boundary, and draft adapter admission.

## Capabilities

- `ethos-repository`: subject=adapter-admission-boundary; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema; facet:authority=source; facet:authority=test; facet:authority=docs; facet:authority=openspec; facet:authority=claim; facet:authority=evidence

## Out Of Scope

- No new product command.
- No new truth store.
- No vendor-specific forbidden-name list.
- No promotion of hosted forge, model, editor, memory, or agent host surfaces to
  product semantics.
