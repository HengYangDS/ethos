## Why

On 2026-07-18, local accepted and candidate refs agree at one commit, while the
four protected refs at the configured GitLab and GitHub forges point to four
distinct commits. Fast-forward-only updates cannot reconcile those histories;
force updates would discard reachable history.

## What Changes

- Establish an evidence-bound maintenance carrier for this exact remote
  reconciliation episode.
- Require the reconciliation head to retain every fresh observed protected tip
  through ordinary merge ancestry before a protected-ref update is considered.
- Keep local proof, local closeout, remote ref observation, and hosted-provider
  observation separate evidence classes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- : add a bounded requirement for normal-merge,
  evidence-first reconciliation of divergent protected refs.

## Impact

The change affects this OpenSpec carrier, claim, Chronicle, and the resulting
Git history. It does not add dependencies, alter a release version or tag, use
a force update, or treat local proof as remote or hosted-provider proof.
