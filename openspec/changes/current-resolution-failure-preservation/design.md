## Context

See `proposal.md`. The shared resolver already owns current authority, official
OpenSpec intent, ordered gaps, one recovery action, and the user-decision fact.
Status, plan, prewrite, hooks, and archive consume those fields. The proof
surface instead continues into `proof_plan()` even when the resolution has
already blocked; its exception path then classifies text locally and can replace
an exact lane recovery with `ethos adopt`.

Three boundaries must remain distinct. Resolution observes current facts and
selects one meaning. Compilation deterministically derives a plan from that
frozen resolution without reading mutable authority again. Attestation issuance
re-observes exact live preconditions before admitting the result. The final
recheck protects against drift; it is not permission to mix a second observation
into the plan or reinterpret an earlier failure.

## Goals / Non-Goals

**Goals:**

- Make non-passing current resolution terminate proof before planner execution.
- Preserve the resolution's verdict, gaps, recovery action, and decision fact
  byte-for-field in the public proof result.
- Stop converting resolver failures into `None` and a synthesized generation
  gap.
- Remove proof-local error classification that guesses recovery from gap text.
- Make proof-plan compilation consume the passing frozen resolution rather than
  rereading Lease or actor state.
- Preserve exact HEAD, tree, repository identity, Lease-generation, and actor
  rechecks at Attestation issuance.
- Prove the same current authority failure across status, plan, prewrite, hook,
  and prove through one behavioral regression.

**Non-Goals:**

- No new resolver, result type, projector, registry, compatibility path, or
  persistent state.
- No weakening or removal of plan binding checks, gate execution checks, or
  issuance-time live observation after resolution passes.
- No repair of unrelated gate-runtime supply, empty-lane landing guidance,
  runtime activation, publication, or adopter state in this Change.

## Decisions

### Treat non-pass as a control-flow boundary, not another planner input

After `_proof_context()` returns, proof examines the selected
`CurrentResolution`. When its verdict is not `pass`, proof constructs its own
presentation state and summary but copies the authoritative verdict,
`required_gaps`, `next_action`, and `user_decision_required`, emits once, and
returns before `proof_plan()`.

Alternative rejected: expand `_proof_plan_error_next_action()` to recognize
every current-resolution gap prefix. That preserves a second policy table and
will drift whenever the resolver adds a new exact gap.

### Compile from one frozen resolution

Once current resolution passes, `proof_plan()` consumes its selected
Commitment, scope, authority, Lease generation, and fresh Git facts. It may
derive proof-specific policy and gate nodes, but it does not call the Lease or
authority resolvers again. This makes the plan a deterministic compilation of
one observation rather than a hybrid of two observation times.

Attestation issuance remains the native currentness boundary. Immediately before
issuance it compares the live HEAD, tree, repository identity, Lease generation,
and actor authority with the plan bindings and rejects drift. This preserves the
race defense without moving mutable observation into compilation.

Alternative rejected: retain planner rereads as an early safety check. They do
not close the execution race and can produce a plan whose Commitment and Lease
generation came from different observations.

### Preserve native post-resolution failures without making the CLI their policy owner

An exception from proof-specific compilation, gate execution, or issuance is not
a current-resolution result. Proof reports the exact gap and routes recovery to
the existing public planning surface. The CLI does not infer adoption or lane
recovery by parsing the exception string.

### Let resolver failures remain explicit

`resolve_generation()` returns `CurrentResolution` rather than swallowing an
unexpected `ValueError` into `None`. Known OpenSpec and Commitment failures are
already represented by `resolve_current_resolution()` as typed non-pass
results. Unexpected failures must retain their exact owner and traceback rather
than become `change_generation_binding_invalid`.

Alternative rejected: add another catch-and-map helper. It would create the
same duplicate interpretation this Change removes.

### Place the regression with the semantic boundary

The cross-surface behavior belongs to current admission resolution. Move the
existing status/plan/prewrite/hook consistency regression out of the hook
command test and extend it with proof. Keep proof-command unit tests for
proof-native planning and execution behavior only.

Alternative rejected: append another integration test to the hook test file.
That would encode physical history rather than semantic ownership.

## Risks / Trade-offs

- **Risk: early return hides proof-specific diagnostics.** → Apply it only when
  current resolution is already non-pass; proof-specific planning has no lawful
  input at that point.
- **Risk: planner exceptions lose specialized recovery.** → Preserve the exact
  gap and route to `ethos plan --changed --json`; add specialized recovery only
  at the native owner, never in a string-prefix table.
- **Risk: a surface-specific summary is mistaken for authority.** → Regress the
  four authoritative fields across all five surfaces while allowing bounded
  presentation fields to differ.

## Migration Plan

1. Add the cross-surface failing regression with proof and prove that the
   planner is not invoked for a non-passing resolution.
2. Add focused proof tests proving that compilation does not reread Lease or
   actor state from a passing resolution while issuance still rejects drift.
3. Add focused proof tests for explicit resolver failure and post-resolution
   native failure.
4. Implement the early terminal projection, frozen-resolution compilation,
   explicit resolver failure, and deletion of the proof-local error-action
   mapper and obsolete expectations.
5. Run focused current-resolution and proof tests, repository-wide reference
   closure, formatting, lint, typing, module-layout, and strict OpenSpec
   validation.
6. Complete exact-HEAD proof, official archive and reproof, candidate and
   accepted exact CAS, immutable runtime readback, and lane retirement.
