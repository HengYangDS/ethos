## Why

The existing rebase context correctly identifies the original `work/*` branch
from Git's `rebase-merge/head-name`, but the lease check still compares the
lease's `expected_head` with detached `HEAD`. Once replay has created a commit,
that comparison rejects a lawful owned-lane rebase even though the named branch
still identifies the lease-bound pre-rebase head.

## What Changes

- Bind the lease comparator to `refs/heads/<rebase-head-name>` only for a
  validated sanctioned Work Lane rebase.
- Preserve detached `HEAD` separately as an observable diagnostic fact.
- Prove the distinction with a real detached replay commit in the hook-admission
  contract test.
- Record the invariant in the repository-governance OpenSpec delta and
  digest-bound evidence.

## Capabilities

- `repository-governance`: subject=work-lane-rebase-write-admission; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=cli; facet:authority=source

## Out Of Scope

- Changing lease holder, lease epoch, branch-role policy, or protected-root
  mutation rules.
- Admitting arbitrary detached branches, inferring a branch without validated
  Git rebase context, or weakening any unresolved/mismatched lease failure.
- Treating this local guard as a cross-host lock, hosted enforcement, or a
  reusable authority grant.
