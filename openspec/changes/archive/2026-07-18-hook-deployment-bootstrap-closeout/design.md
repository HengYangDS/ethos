# Design

## Context

The accepted checkout owns the shell-hook/CAS boundary. The candidate checkout
owns the proposed semantic runner. When the proposed tree changes the shell
hook itself, an ordinary dual-ref transaction needs a deployment bootstrap: `main` is still
checked by the accepted-old shell before that shell can be replaced.

## Design

Closeout first compares the immutable accepted and candidate blobs for
`.githooks/reference-transaction`. Only when an `accepted_ff` mirror exists,
`dev` is behind candidate, and that blob differs, it enters a bounded bootstrap
mode:

1. carry the exact candidate proof and write the ordinary one-shot intent for
   the `dev` transition;
2. execute the official compare-and-swap for `dev` only through the incumbent
   fail-closed hook;
3. reset the accepted checkout to the newly accepted candidate tree;
4. write the ordinary one-shot intent for `main` and execute its official
   compare-and-swap through the now-promoted hook;
5. synchronize the linked release worktree and verify cleanliness.

Both legs retain topology, proof, and exact-intent checks. The first leg is
permitted only because `dev` is the configured accepted ref and the candidate
semantic reducer validates it. The second leg carries no new source admission;
it completes the declared mirror. If it cannot complete, the command reports a
specific incomplete-mirror state for deterministic retry; it never reports
accepted closeout as complete.

## Alternatives

- Mutate the accepted tracked hook before closeout: rejected as protected-root
  editing.
- Temporarily point `core.hooksPath` to the candidate: rejected as an
  ungoverned bypass.
- Let the candidate approve raw ref updates: rejected because the existing
  candidate runner and one-shot marker are still mandatory on both legs.

## Proof Strategy

- Add a failing armed-hook regression with an incumbent shell that routes only
  `dev` through the candidate, deliberately denying the incumbent semantic
  reducer for `main`.
- Prove that managed closeout performs the two official legs and converges both
  protected refs without a bypass.
- Run focused closeout/ref-hook suites, ShellCheck, parity, OpenSpec lifecycle,
  and a fresh executed proof before candidate land.
