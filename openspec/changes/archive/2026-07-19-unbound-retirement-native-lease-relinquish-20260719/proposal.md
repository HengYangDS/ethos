## Why

The accepted exceptional unbound-retirement route requires that no active lease
exist before admission, yet its receipt requires the lease to be absent after
the effect. A holder-owned, exact lease therefore deadlocks a ref-only residue:
there is no native transition that can relinquish the exact generation without
manual state deletion.

## What Changes

- Keep foreign or mismatched leases fail-closed.
- Permit the native exceptional command, after all accepted Chronicle, exact
  head, ancestor, and destructive controls pass, to revoke only the invoking
  holder's exact lease generation through its existing CAS primitive.
- Reobserve all retirement bindings after relinquishment before the existing
  compare-and-delete ref effect; retain local attempt and receipt records.

## Capabilities

- `repository-governance`: subject=exceptional-unbound-native-lease-relinquish; reuse=extend; change=modify; facet:lifecycle=validation,runtime,archive; facet:surface=cli,docs,openspec,evidence; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Raw SQLite, Git-ref, or generic lease deletion; foreign lease takeover;
  linked-worktree retirement; remote mutation; hosted CI; GitLab/GitHub
  publication; or retiring any ref other than a separately admitted target.
