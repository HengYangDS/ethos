## 1. Contract and implementation

- [x] 1.1 Add the candidate-runner and candidate-first closeout contract deltas.
- [x] 1.2 Implement accepted-hook resolution of the exact clean candidate runner.
- [x] 1.3 Preserve local checkout runtime binding for non-accepted ref events.

## 2. Regression and archive readiness

- [x] 2.1 Add and run skew, raw-ref, sanctioned-closeout, and candidate-refresh regressions.
- [x] 2.2 Validate shell/runtime binding, Python lint, claim/Chronicle digest, and official OpenSpec lifecycle.
- [x] 2.3 Archive the completed Change through the official OpenSpec CLI.

## Post-archive lifecycle boundary

Generic parity evidence and HEAD-bound proof are regenerated only after the
archive has established the exact lane tree. Candidate landing, accepted closeout,
publication, and retirement remain separate governed transitions.
