# Design

## Context

See [proposal.md](proposal.md). `run_command` already keeps a command's complete result in its
`CompletedProcess`, and with `check=True` raises Python's `CalledProcessError`, which carries argv,
exit status and both streams. The loss happens above it, where each boundary rebuilds a message or a
dictionary by hand.

## Goals / Non-Goals

**Goals:**

- Every boundary that turns a native command failure into evidence keeps argv, exit status or bound,
  and both complete streams; human-facing messages stay bounded.
- Provider gates and command gates classify an expired deadline the same way.

**Non-Goals:**

- Retaining the streams of successful commands, or changing what a gate retains on success.
- Changing a gate's declared bound; `timeout_seconds` keeps its meaning.

## Decisions

- **The native exception is the carrier.** `CalledProcessError` and `TimeoutExpired` already hold
  the complete result, so boundaries raise or chain them instead of formatting tails. One function
  projects them into evidence, replacing the six inline decoders. Rejected: a new ETHOS exception
  type, which would duplicate the standard library's.
- **An expired provider deadline is unknown, not blocked.** The provider did not decide, as with a
  command gate's exit 124. The diagnostic names the bound and the elapsed seconds so a reader can
  tell a tight bound from a hung run.
- **Unobserved stays for a successful but incomplete classification.** Git exited zero and named
  fewer paths, so there is no failure to keep; the caller still blocks the input.

## Risks / Trade-offs

- [Complete streams enlarge a failure's evidence] → Only failures carry them, and the native tool
  wrote exactly that output.
- [A gate that timed out now reads unknown instead of blocked] → Both refuse admission; only the
  reason changes, to the one the reader needs.
