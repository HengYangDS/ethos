## Context

The shared writer flushes file bytes, links the temporary file to its immutable
digest path, and then opens the parent directory for `fsync`. That final POSIX
durability barrier is unsupported by Windows Python and aborts otherwise valid
package materialization after the wheel has been built.

## Goals / Non-Goals

**Goals:**

- Keep one content-addressed publication implementation on all hosts.
- Preserve the strongest available durability semantics per platform.
- Keep collision and byte-identity behavior unchanged.

**Non-Goals:**

- No alternate Windows store, broad exception suppression, retry layer, or
  runtime-activation redesign.

## Decisions

The writer will continue to flush the temporary file and publish it with the
existing atomic link operation on every platform. It will perform the additional
parent-directory `fsync` only on POSIX, where directory descriptors are a
supported durability primitive. Platform selection is explicit before the
operation; a genuine POSIX permission or I/O failure remains fatal.

This is preferred to catching `PermissionError`, because exception swallowing
would hide real storage failures and would make behavior depend on error text.

## Risks / Trade-offs

- Windows cannot receive the POSIX directory-entry durability barrier; the
  atomic link and file `fsync` remain intact. Hosted Windows conformance proves
  the supported path.
- Platform branching can drift; a focused regression asserts that Windows never
  attempts to open the parent directory while POSIX still does.
