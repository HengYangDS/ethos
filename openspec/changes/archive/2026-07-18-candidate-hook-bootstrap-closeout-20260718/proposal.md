## Why

The accepted-root reference-transaction hook is itself a tracked control file.
A candidate may correctly repair that hook, but the accepted checkout still
runs its older shell file until the atomic closeout completes. The earlier
release-mirror repair therefore cannot govern its own first promotion by source
presence alone: the incumbent hook remains the executable boundary for the
transaction and can reject the candidate's legitimate `main` transition.

## What Changes

- Bind the official closeout `git update-ref` invocation to the exact clean
  candidate hook directory for that one atomic transaction **only when the
  candidate replaces the tracked reference-transaction hook**.
- When that control path is replaced, require a present executable candidate
  reference-transaction hook before the official transaction begins; do not
  fall back to an absent candidate hook. Unchanged-hook closeouts preserve
  their existing configured-hook route.
- Keep raw Git operations bound to the configured incumbent hook path.
- Add an armed integration regression with a deliberately legacy accepted hook:
  raw `dev` and `main` moves block; a candidate hook update then permits only
  the sanctioned atomic closeout.
- Classify a rejected atomic CAS by observed post-failure refs rather than
  asserting a concurrent accepted advance when neither ref moved.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=candidate-hook-bootstrap-closeout; reuse=extend; change=modify; facet:lifecycle=mutation,validation; facet:surface=hook,cli,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Out of Scope

- No environment-variable bypass, hook disabling, Git configuration rewrite,
  raw accepted-ref update, remote publication, GitLab action, worktree cleanup,
  or foreign-lane mutation.
- No weakening of exact closeout-intent, candidate-head, proof, fast-forward,
  or candidate-external control-receipt obligations.

## Impact

The change is restricted to the local closeout CAS hook selection, its failure
classification, the real armed-hook regression, and repository-governance
records.
