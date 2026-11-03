# Design

## Context

See [proposal.md](proposal.md). `_execute_command` passes its timeout to `Popen.communicate`.
`tests.support.subprocesses.ready_descendant` patches `communicate` so that it first waits, up to
10 seconds, for one byte that the child sends over a loopback socket, and other process tests
already use it to start fault injection at a known point of the child.

## Goals / Non-Goals

**Goals:**

- The timeout tests check that a timed-out command keeps the output its child wrote, whatever the
  host's load before the child writes.

**Non-Goals:**

- Any change of the process adapter, whose timeout semantics are correct.

## Decisions

- **The child writes before its handshake.** It writes and flushes its stdout and stderr, then sends
  the readiness byte and blocks on its socket. The adapter's 1-second timeout starts after that
  byte, so the output is complete when it expires.
- **No socket-closure check.** Unlike the POSIX-only tests that use the helper, these tests also
  run on Windows, where a killed peer can reset the connection instead of closing it; other tests
  own the cleanup of a timed-out command.
- **No longer timeout.** A longer timeout slows every run and still races on a slower host.

## Risks / Trade-offs

- [A host too slow for the child to connect within 10 seconds] → The test fails with the
  handshake's own timeout, which names the cause, instead of an empty capture.
