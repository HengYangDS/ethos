## Why

`ethos hook install` currently activates an immutable runtime and generated
hooks without treating Git-common SQLite state as part of the same transition.
An adopter carrying the previous Lease table can therefore switch to a runtime
that immediately rejects every command with
`state_schema_lease_table_definition_mismatch`. Runtime construction also
discovers missing offline lock artifacts only after installation work has
started.

## What Changes

- Make hook installation fill one Git-common dependency cache from the exact
  lock, then prove the same closure by installing it offline before changing
  selector, hooks, Git configuration, or SQLite state.
- Recognize the exact previous Lease schema and migrate only its still-live
  lane, holder, generation, and expiry semantics.
- Keep the SQLite migration transaction uncommitted until runtime and hook
  activation has passed; rollback state, selector, and Git configuration on any
  failure.
- Expose an explicit authorized reset through the same hook-install operation
  when legacy rows cannot be mapped safely; never require manual SQLite edits.
- Make public failures report the exact state boundary and one executable next
  command.

## Out of Scope

General result-projection convergence, Work Lane recovery, temporary-resource
scavenging, and remote publication remain separate Changes. This Change adds
no second state store, migration registry, compatibility reader, or persistent
journal.
