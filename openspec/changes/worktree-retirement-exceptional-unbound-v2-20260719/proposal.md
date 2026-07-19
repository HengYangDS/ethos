## Why

`ethos lane retire unbound` correctly refuses ordinary deletion of an unbound
Work Lane ref. The generic exceptional resolver deliberately requires a linked
worktree and therefore cannot act on a ref-only residue. An accepted-ancestor
ref with no linked worktree and no active lease needs a narrow native route that
remains fail-closed without depending on a particular agent host.

## What Changes

- Extend `ethos lane retire unbound` with an exceptional apply route for one
  exact accepted-ancestor Work Lane ref.
- Require an accepted, target-specific Chronicle; exact head; empty linked
  worktree and lease state; `--authorize`; `--break-glass`; and
  `--confirm-irreversible` before any effect.
- Reobserve the complete target and protected-ref bindings immediately before
  the compare-and-delete ref update, then write no-clobber local attempt and
  receipt records outside the repository worktree.
- Keep all non-qualifying unbound refs blocked. Do not add a generic delete
  command, raw-ref fallback, host-specific identity rule, or foreign-lane
  takeover path.

## Capabilities

- `repository-governance`: subject=exceptional-unbound-lane-retirement; reuse=extend; change=modify; facet:lifecycle=validation,runtime,archive; facet:surface=cli,docs,openspec,evidence; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Codex, any provider, account, UI, session, host-worktree recovery, or host
  filesystem policy.
- Generic or batch unbound-ref deletion, raw Git fallback, force worktree
  removal, lease deletion, foreign-lane takeover, remote mutation, and hosted
  CI acceptance.

## Impact

- The lane-retirement adapter and CLI contract.
- Unit and CLI contract tests for unbound retirement.
- The canonical command reference and repository-governance specification.
- Local-only attempt and receipt records under the accepted-root sibling record
  root; remote publication, hosted CI, and host-session recovery remain outside
  this Change.
