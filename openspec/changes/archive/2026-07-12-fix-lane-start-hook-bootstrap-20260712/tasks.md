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
- [x] 3.2 Run the HEAD-bound proof for the archived implementation after the
  refreshed parity evidence is committed.
- [x] 3.3 Keep candidate landing, accepted-root closeout, and local publication
  readiness as separate governed follow-on transitions; remote publication stays
  deferred and is never pushed by this change.
