# Evidence Lifecycle Signal Hygiene

## Summary

Replace the ambiguous active-claim HEAD advisory with an explicit evidence
freshness contract. A dated, digest-bound Chronicle is durable historical
support; it is not silently represented as current-HEAD proof.

## Scope

- Require active claims to declare `historical`, `head_bound`, or
  `semantic_scope` evidence freshness.
- Keep historical delivery evidence durable without emitting false currentness
  warnings.
- Require exact HEAD or declared semantic-target digest when a claim requires
  currentness.
- Migrate every existing active claim to an explicit historical contract.

## Non-goals

- Do not retroactively claim that historical delivery evidence was executed at
  the present HEAD.
- Do not add a second claim store, a waiver, or a compatibility default.
- Do not alter foreign Work Lanes or remote publication state.
