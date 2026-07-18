## 1. Candidate-hook bootstrap

- [x] 1.1 Route only official atomic closeout CAS through the exact candidate
  hook directory.
- [x] 1.2 Fail closed for a missing or non-executable candidate hook and
  distinguish hook rejection from observed accepted-ref concurrency.

## 2. Regression evidence

- [x] 2.1 Add an armed integration regression with a legacy accepted hook and
  upgraded candidate hook; prove raw protected moves block and sanctioned
  accepted_ff closeout advances both refs atomically.

## 3. Authoring closeout

- [x] 3.1 Run focused tests and OpenSpec/claim lifecycle validation; archive
  the carrier and run an exact HEAD-bound default proof after this implementation
  commit establishes the immutable carrier head.
- [x] 3.2 Record candidate landing, candidate-external receipt issuance, and
  accepted-root local closeout as subsequent governed transitions; this carrier
  asserts authoring readiness only and does not mark any of those transitions
  complete.
