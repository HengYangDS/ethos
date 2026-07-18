## 1. Authority and input capture

- [x] 1.1 Start an owner-bound Work Lane from the current candidate head.
- [x] 1.2 Record the four protected remote tips in a dated Chronicle.
- [x] 1.3 Create and bind the active claim, OpenSpec carrier, and scope.

## 2. History-preserving reconciliation

- [x] 2.1 Re-observe all four remote inputs immediately before merging.
- [x] 2.2 Merge each observed remote tip with normal merge commits and review every conflict resolution.
- [x] 2.3 Verify the resulting head is a descendant of all four observed tips.

## 3. Historical archive transfer

- [x] 3.0 Compress four equivalent TOML layout lines in the closeout manifest
  without changing parsed configuration or source-budget policy.
- [x] 3.1 Record the r5 continuation and active episode-claim binding for the
  unfinished parity, proof, closeout, remote-observation, and retirement work.
- [x] 3.2 Preserve the r3 archive as historical evidence without asserting the
  transferred lifecycle work completed in r3.

## Deferred Lifecycle Work (owned by r5, not completed in r3)

- Refresh parity and execute changed-plan and HEAD-bound proof.
- Land to `candidate/dev`, run the candidate-external closeout verifier, and
  align local `dev`, `main`, and `candidate/dev`.
- Run ordinary per-ref push dry-runs and perform no-force protected updates only
  when each dry-run is accepted.
- Re-observe GitLab and GitHub refs, then collect provider/API and hosted-CI
  observations without inferring one result from another.
- Update the claim and Chronicle with final bounded evidence and retire the
  landed owner-bound Work Lane.

These are explicit continuation duties rather than retroactive r3 completion
claims.  Their evidence is bound to
`openspec/changes/remote-reconciliation-continuation-r5-20260718`.
