## Context

The hook's shell layer owns the atomic Git transaction boundary, but semantic
admission for an accepted-root promotion must be evaluated from the candidate
tree being promoted. The existing hook already does this for `dev`; an
`accepted_ff` closeout also moves `main` in the same transaction.

## Decision

At prepared phase, the hook reads the local role declaration. It resolves the
candidate semantic runner for:

1. the accepted branch; and
2. the release branch only when `release_mirror = "accepted_ff"`.

The runner must be clean, linked to the live candidate head, and execute the
same `ethos hook ref-transaction` reducer for the exact ref transition. Other
refs retain the existing incumbent/fail-open path. This preserves the current
asymmetry: protected closeout transitions fail closed; unrelated branch work
is not newly coupled to candidate-runtime availability.

## Safety properties

- The candidate semantic reducer still consumes a distinct one-shot intent for
  each exact ref move and re-checks proof, fast-forward, and live-candidate
  containment.
- A raw `dev` or `main` move cannot borrow an intent and remains blocked.
- The atomic `git update-ref --stdin` transaction remains all-or-nothing.
- The remediation is local-closeout only; no external publication state is
  inferred.

## Proof

The real hook is installed in a scratch repository with `accepted_ff` policy.
The test blocks raw moves for `dev` and `main`, damages the accepted checkout's
hook reducer, then invokes sanctioned closeout and requires both refs to reach
the candidate head. This fails under the prior runner selection and passes only
when both protected transitions use candidate semantics.
