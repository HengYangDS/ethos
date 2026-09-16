## Context

The exact failed public preview is retained in
`build/evidence/quality/commit-integrity/self-identity-publication-preview.json`.
The commit-range owner reports `update_kind=repair` and a verified
`integration_baseline`, but the publication consumer only recognizes the
terminal `state=repaired_history`. Ordinary descendants report `state=admitted`.

## Goals / Non-Goals

Preserve the range owner's verified relation across the full publication
boundary. Keep direct replacement and later forward advancement distinct.
No second provenance resolver, durable cache, blanket non-fast-forward permission,
remote-only workaround, changed author policy or adopter mutation.

## Decisions

Use repair classification for proof requirements, and the verified replacement
as the baseline for ordinary accepted advancement. Keep the existing direct
replacement behavior separate. Candidate equality and forward topology still
apply to descendants; proof and accepted-effect obligations remain independent.
A boolean bypass for every repaired descendant is rejected because it would
silently remove candidate validation.

Add a real repair-to-signed-descendant fixture at the publication consumer. It
must reach public pre-push and receipt-bound two-peer publication. Missing proof,
missing accepted effect, stale candidate and unsigned descendant must fail.
The earlier range tests remain; they were insufficient to demonstrate this
higher boundary, not incorrect evidence of their narrower behavior.

## Risks / Trade-offs

- Cross-boundary drift: assert the same verified baseline and independent gaps
  through the public commands before running the full proof.
- Expensive history verification: keep this fix bounded; no cached authorization.
  Existing P5 owns observation sharing under complete input and trust bindings.

## Migration Plan

Prove and accept the fix through the existing lane, install the exact accepted
runtime, derive a fresh two-peer request, apply its exact CAS, and independently
read back each peer. Retain failed attempts and repair recovery bytes. Do not
retry the unchanged blocked preview or relabel its verdict.
