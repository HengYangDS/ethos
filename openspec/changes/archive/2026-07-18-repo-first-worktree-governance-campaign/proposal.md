## Why

ETHOS observes a large portfolio of linked Work Lanes whose location, ownership, dirty state, recovery value, and retirement authority cannot be inferred from Git registration alone. The product needs one repository-first campaign that makes recovery, deletion, migration, and retirement explicit without importing workstation-wide authority or mutating foreign lanes by visibility.

## What Changes

- Add a dedicated strict-serial campaign for repo-first worktree governance v2.
- Add `--campaign` selection to the read-only campaign closeout report so one campaign can be evaluated without unrelated active campaigns becoming implicit blockers.
- Bind the bootstrap lane, OpenSpec carrier, claim, scoped evidence, implementation contract, and a bounded source-budget record to the campaign’s first step.
- State the frozen directory grammar and authority split as repository-governance behavior, while deferring destructive recovery and migration mechanics to later campaign steps.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=repo-first-worktree-governance; reuse=extend; change=modify; facet:lifecycle=authoring; facet:surface=cli,docs,openspec,evidence; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- This bootstrap does not capture, move, retire, delete, prune, or modify any foreign, unknown, App-managed, or runtime-managed worktree.
- It does not create a workstation-wide lifecycle authority, invoke Kopia, or use Git stash as recovery machinery.
- It does not implement later recovery-package, deletion-admission, records, migration, or retirement-saga steps; those remain independently OpenSpec-backed campaign steps.
- It does not settle unrelated source-budget debt or import another lane’s growth allowance; the bootstrap record is bounded to this carrier and its declared deletion wave.

## Impact

Affected surfaces are the campaign read model and CLI, repository-governance specification, campaign documentation, one dedicated campaign manifest, one active claim, one Chronicle, and focused CLI regression coverage. No remote or external service is changed.
