## 1. Hook admission design

- [x] 1.1 Record the fresh Work Lane bootstrap boundary in proposal, design, and
  repository-governance delta.

## 2. Implementation and regression coverage

- [x] 2.1 Restrict the no-runtime fast path to fresh `work/*` creation or
  reassertion events.
- [x] 2.2 Add an armed-hook regression proving fresh Work Lane creation does
  not invoke `uv`.

## 3. Verification and lifecycle

- [x] 3.1 Run focused hook tests, formatting/lint checks, and strict OpenSpec
  validation.
- [ ] 3.2 Run the HEAD-bound proof, land through the candidate train, and
  complete accepted-root closeout with a new external receipt.
- [ ] 3.3 Recheck local publication readiness and record remote publication as
  deferred without pushing.
