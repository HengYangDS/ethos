## 1. Runtime-boundary design

- [x] 1.1 Record the narrow marked semantic-Python re-entry contract, scope,
  Claim, and Chronicle without widening hook or ref authority.

## 2. Test-first implementation

- [x] 2.1 Add a deterministic regression with a valid current semantic runtime
  and a failing fake `uv` to prove marked re-entry bypasses synchronization.
- [x] 2.2 Add the minimal bootstrap guard before any semantic-Python `uv`
  synchronization while preserving all unmarked and invalid-runtime fallbacks.

## 3. Verification and lifecycle

- [x] 3.1 Run focused runtime-wrapper and armed-hook regressions plus strict
  OpenSpec and Claim validation.
- [x] 3.2 Refresh generic parity and run one exact-HEAD executed proof after
  the final carrier state is committed.
- [x] 3.3 Confirm archive readiness after the completed implementation and
  pre-archive proof are recorded; official archive, candidate land,
  accepted-root closeout, lane retirement, local publish readiness, and remote
  publication remain separate governed transitions.
