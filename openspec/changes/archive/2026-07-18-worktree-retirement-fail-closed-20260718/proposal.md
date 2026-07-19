## Why

Ordinary Work Lane retirement still contains destructive paths that can delete a
ref before Git has confirmed the linked checkout can be removed. An unbound
`work/*` ref has no locally observable directory or uncommitted-file inventory,
so its missing worktree registration is not evidence that deletion is safe.

## What Changes

- Make routine landed and superseded linked-lane retirement reobserve the exact
  worktree/ref/head immediately before effect, remove the clean worktree without
  `--force`, then delete only the exact observed ref.
- Block ordinary unbound-ref retirement; require the later evidence-bound
  deletion-admission route rather than inferring abandonment from no linked
  worktree.
- Reconcile the completed campaign bootstrap as retired and activate only this
  strict-serial successor.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=worktree-retirement-fail-closed; reuse=extend; change=modify; facet:lifecycle=validation,runtime,archive; facet:surface=cli,openspec,evidence; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Capturing or deleting dirty content, creating recovery packages, or clearing
  retained packages; those belong to later campaign slices.
- Retiring, moving, pruning, repairing, or inferring abandonment of any
  foreign, missing, unknown, App-managed, or runtime-managed Work Lane.
- Remote publication, GitHub or GitLab state, hosted CI, releases, credentials,
  and workstation-wide lifecycle authority.

## Impact

Affected surfaces are the linked-lane retirement adapters, regression tests,
the campaign ledger, claim and Chronicle evidence, and repository-governance
specification. No recovery package, exceptional deletion, migration, foreign
lane action, remote publication, or hosted provider action is performed.
