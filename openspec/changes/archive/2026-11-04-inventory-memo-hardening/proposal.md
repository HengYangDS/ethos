# Proposal

## Why

The runtime inventory memo, `src/ethos/adapters/repo/runtime/inventory_memo.py`, lets a command
reuse a payload file's recorded digest while the file's exact state is unchanged. The design safety
review of 2026-11-04 found two weaknesses that predate the Windows memo design:

- `open_inventory_memo` reads any memo in the host store without checking who owns it.
  `host_store_root()` honours `XDG_DATA_HOME`, so on a host whose data home is shared between
  accounts another account can plant entries that make ETHOS skip hashing a payload file it
  changed.
- `InventoryMemo.save()` leaves its temporary file behind when the final replace fails. When the
  dump fails, it unlinks the temporary while the stream is still open, which Windows refuses.

## What Changes

- A memo serves only from a directory that is a real directory owned by the current user. Its
  entries are read only while group and others cannot write that directory, and only from a file
  that the current user owns and that group and others cannot write. Otherwise every payload file
  is hashed, as without a memo.
- ETHOS creates the memo directory with mode `0700`, and a save tightens an owned directory that
  is looser. Windows keeps the memo off, as today; enabling it there requires the equivalent owner
  check.
- Every failed save removes its temporary file, after closing its stream.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No specification describes the memo. It remains an internal saving whose absence costs only
hashing, so `skip_specs: true` applies.

## Impact

`src/ethos/adapters/repo/runtime/inventory_memo.py`,
`tests/unit/adapters/repo/runtime/test_inventory_memo.py` and `CHANGELOG.md`.
