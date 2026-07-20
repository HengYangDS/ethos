## Why

An `accepted_ff` local closeout atomically advances the accepted ref and its
release mirror. The armed `reference-transaction` hook chose the candidate
semantic runner for the accepted ref only. The release-mirror ref therefore
used the incumbent accepted checkout while that checkout was necessarily one
tree behind the candidate being promoted. This can reject a legitimate atomic
closeout and is reported too broadly as concurrent accepted advancement.

## What Changes

- Treat the release-mirror ref as a protected candidate-semantic surface only
  when the current repository policy declares `release_mirror = "accepted_ff"`.
- Run the exact clean candidate runner for both protected prepared transitions.
- Keep independent release branches and ordinary refs on the existing
  non-protected path.
- Add an armed-hook integration regression that blocks raw moves of both refs
  while proving a sanctioned closeout advances both after the incumbent reducer
  is intentionally made unusable.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=accepted-ff-release-mirror-candidate-runner; reuse=extend; change=modify; facet:lifecycle=mutation,validation; facet:surface=hook,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Out of Scope

- No change to remote publication, forge protection, GitLab, or any runner.
- No relaxation of closeout-intent, proof, fast-forward, or candidate-head
  checks.
- No worktree, branch, or foreign-lane cleanup.

## Impact

The change is limited to ETHOS's local reference-transaction hook contract,
its focused armed-hook proof, and repository-governance specification.
