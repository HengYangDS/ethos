## Context

The target began as a detached registered worktree whose original historical
branch ref was absent.  Its committed HEAD is already in accepted history, but
four unique dirty files prevent clean retirement.  Current accepted source has
independently evolved the useful topology and CEL responsibilities.

## Decision

First freeze the exact detached observation and dirty patch digest.  Recreate
the historical branch only at the exact detached HEAD and attach it to the same
worktree without changing bytes.  Promote a current-base semantic judgment,
then use the existing native preserve-retire lifecycle after accepted closeout.

Do not replay identity-keyed weak-reference caches or directory-level evidence
collapse.  Current whole-decision caching and exact denied-path reporting are
the authoritative replacements.

## Risk Controls

- Branch reconstruction must not change HEAD, index, or working bytes.
- Any owner, lease, Claim, process occupancy, ref, dirty-path, patch, accepted
  head, Chronicle, or package drift blocks effect.
- Native preservation precedes branch/worktree removal.
- Package clear requires a later accepted exact-manifest decision.
- No other lane or remote is in scope.
