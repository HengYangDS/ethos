## Context

The semantic kernel already defines a four-field Lease, transient Commitment,
closed verdict union, schema-version-`2` result, and pure Continuation. The
remaining defect is ownership: current authority and remediation are assembled
again in status, plan, prewrite, hook, and lifecycle projectors.

## Goals / Non-Goals

**Goals:**

- Establish one typed current-resolution owner over fresh repository facts.
- Make result Continuation structural rather than text-derived.
- Delete duplicate gap priority, state selection, and next-action fallbacks.
- Preserve exact diagnostics and one executable recovery action.

**Non-Goals:**

- No new persistent state, workflow store, registry, compatibility layer, or
  tracked carrier.
- No remote-publication transaction changes in this atom; peer-ref ordering and
  temporal parity are handled by the later remote-effect atom.
- No OpenSpec dependency upgrade or adopter-specific policy.

## Decisions

### Replace generation binding with current resolution

Evolve the existing current-generation binding owner into a typed current
resolution that carries the same selected Commitment and path attribution plus
the already-existing current authority, ordered gaps, exact action, and explicit
user-decision fact. Consumers request the operation they are evaluating and do
not reinterpret the result.

This replaces, rather than wraps, the current binding and command-local action
selection. A second resolver, rule registry, or error taxonomy is rejected.

### Keep one result envelope and make judgment explicit

`EthosResult` keeps schema version 2 and its existing public fields.
`user_decision_required` becomes an ordinary validated boolean input.
`continuation` remains computed: explicit user judgment wins, a non-pass result
blocks, a passing result with an action continues, and a passing result without
an action is done.

Parsing `next_action`, matching English phrases, and recognizing gap suffixes
are deleted because presentation text cannot own authority semantics.

### Project, do not decide

CLI and hook modules may choose bounded summaries and output formatting. They
must use the resolution's verdict, state, ordered gaps, action, and decision
fact unchanged. Operation adapters retain native effect-specific checks; they
return structured facts to the resolver instead of manufacturing a second
public result.

### Preserve positive diagnostics

Tool and projection failures carry exact observed facts. Recovery is selected
from the failed positive capability boundary, not from a negative exception
list. Generic placeholders and unrelated adoption advice are deleted.

## Risks / Trade-offs

- **Risk: broad constructor migration** → convert one projection family at a
  time under focused contract tests, then remove the old helper immediately.
- **Risk: an operation needs a unique effect precondition** → keep the
  precondition in its native adapter, but feed its structured outcome into the
  common result resolution instead of adding command-specific result logic.
- **Risk: schema-version-2 readers carried derived booleans** → retain the
  same wire field and validate it on round-trip; only its ownership changes.

## Migration Plan

1. Establish failing result-algebra and cross-surface consistency tests.
2. Replace current-generation binding with the typed current resolution.
3. Move status, plan, prewrite, and hook projection to that owner.
4. Delete command-local action/state interpretation and text parsing.
5. Regenerate and validate the result schema, run focused and affected gates,
   then complete the normal proof, archive, promotion, runtime-readback, and
   lane-retirement sequence.
