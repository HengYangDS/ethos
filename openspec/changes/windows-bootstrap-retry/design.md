# Design

## Context

See [proposal.md](proposal.md). `prepare_mise` stages the executable in a temporary directory under
the tool cache, verifies its version by running it, then calls `candidate.replace(executable)`
while it holds the bootstrap lock. On Windows a file that was just run or written can stay open
for a moment, for example while the antivirus scanner reads it.

## Goals / Non-Goals

**Goals:**

- A brief hold on the just-verified executable no longer fails the job.

**Non-Goals:**

- The tools that Mise installs itself, which keep Mise's own handling.

## Decisions

- **Retry only the codes that a held file raises.** `ERROR_SHARING_VIOLATION` (32) and
  `ERROR_ACCESS_DENIED` (5), read from the error's `winerror`; every other error propagates on the
  first attempt.
- **Bounded backoff.** Ten attempts whose waits double from 0.1 seconds to at most 2 seconds, about
  13 seconds in all.

## Risks / Trade-offs

- [A lasting permission problem waits before it fails] → It fails with the same error after one
  bounded wait.
