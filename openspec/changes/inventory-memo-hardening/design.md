# Design

## Context

`open_inventory_memo` derives `<host store>/runtime-inventory/<hash>.json` and trusts its entries
when the schema and root match. `save` writes a temporary file in the same directory, then replaces
the memo with it. The memo only saves hashing: a missing or refused memo makes the inventory hash
every file. A wrong entry is the only way the memo can hide changed bytes.

## Goals / Non-Goals

Goals:

- An entry is reused only from a memo that only the current account could have written.
- No failed save leaves a temporary file.

Non-goals:

- The Windows memo, which takes its keys from a file handle and admits volumes; that is a later
  Change, and the memo stays off on Windows.
- Defending against the same account. Local guards never claim to stop a same-user writer.

## Decisions

1. Read the memo through one descriptor opened with `O_NOFOLLOW`. Before reading, check its owner
   and mode with `fstat` on that descriptor, so the file that is checked is the file that is read.
2. Check the directory with `lstat`. It must be a directory, not a symbolic link, and owned by the
   effective user. A directory that fails this check serves no memo. An owned directory that group
   or others can write yields no recorded entries, but it still lets the save heal it.
3. Create the directory with mode `0700`. A save re-checks the directory after creating it, because
   another account could create it in a shared parent between open and save. A save tightens an
   owned, looser directory to `0700`; a directory that another user owns is never written.
   `tempfile` creates the temporary with mode `0600`, and `os.replace` keeps that mode.
4. A refused memo file inside an owned directory is read as empty, not deleted. The next save
   replaces it atomically.
5. `save` closes the stream before any removal, and removes the temporary in a `finally` clause
   whenever the replace did not happen. A failed save still never raises an `OSError` to its
   caller.

Alternatives considered:

- Naming each memo file by user ID does not stop another account writing that name.
- Signing the entries needs a key that ETHOS does not hold for this purpose.

## Risks / Trade-offs

- A memo directory left group-writable by an earlier release serves no entries until the next save
  tightens it. The cost is one pass of hashing.
- Windows remains memo-free. The stream-before-unlink order is therefore enforced by the code's
  structure. Tests can observe it once the Windows memo Change runs this test module on Windows.
