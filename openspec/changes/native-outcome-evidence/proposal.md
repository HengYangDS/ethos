# Proposal

## Why

A failed or timed-out native command loses part of its result at several boundaries, so the evidence
that explains a failure is gone when someone needs it.

- The shared-supply Mise call keeps only the last 2,000 characters of one stream
  (`tools/ci/delivery/distribution.py:364-368`, GitHub issue #19).
- A failed Git text classification returns `None`, so its caller reports only
  `authored_text_unobserved` without Git's exit status or stderr
  (`src/ethos/adapters/repo/git_attributes.py:74-75`, issue #16, first open item).
- A provider gate whose deadline expires reports `gate_provider_error` and blocks, without its bound
  or the elapsed time, while a command gate reports `gate_timeout` as unknown
  (`src/ethos/adapters/gates/verification.py:153-165`, GitLab issue #2).
- Six places decode a failed command's streams with the same inline expression (`runner.py:156-166`,
  `formatting.py:504-515`, `native/attempt.py:157-167`, `native/inputs.py:195-204`,
  `javascript/behavior.py:351-360`, `mutation/publication/observation.py:36-40`).

## What Changes

- One owner in the process adapter projects a failed or timed-out command into its complete result:
  argv, exit status or bound, and both streams decoded without loss of presence. Every boundary
  above uses it.
- A provider that raises a native command failure keeps that result in the gate's
  `gate_provider_error` diagnostic; a provider that times out reports `gate_timeout:<gate>` as
  unknown with its bound and elapsed seconds, as a command gate does.
- Git classification failure raises Git's own `CalledProcessError`; incomplete classification by a
  successful Git still reads as unobserved.
- The Mise boundary raises its bounded message from the complete `CalledProcessError`, and the
  package acceptance's terminal evidence records every native command failure in its cause chain.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: native command failures and provider timeouts keep their complete outcome.

## Impact

`src/ethos/adapters/process.py`, the six decoding sites, `src/ethos/adapters/gates/verification.py`,
`src/ethos/adapters/repo/git_attributes.py`, `tools/ci/delivery/distribution.py`,
`tools/ci/delivery/acceptance/receipt.py`, their tests and the `quality` specification.
