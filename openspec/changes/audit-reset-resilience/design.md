# Design

## Context

See [proposal.md](proposal.md). `_observe` in `tools/ci/dependency_audit.py` repeats only an npm
observation whose reason is `advisory_request_failed`, three times with two-second pauses.
`interpret_native_audit` reads stdout and the exit code. `evaluate_dependency_acceptance` checks
that the receipt is consistent, then parses each check's output for findings.

## Goals / Non-Goals

Goals:

- A burst of resets of a few minutes does not fail a proof.
- An audit that observed nothing says so, with the native reason.

Non-goals:

- Treating an unobserved ecosystem as passing. It stays unknown after the backoff.
- Retrying anything other than a failed advisory request.

## Decisions

- **Classify by stderr, for Python only.** uv reports a failed request on stderr with
  `error sending request for url`, and writes no stdout. Interpretation gains the stderr. A Python
  check is `advisory_request_failed` only when the exit code is non-zero, stdout is empty and
  stderr names a failed request. Any other empty output stays `native_output_invalid`.
- **One backoff for both ecosystems.** The pauses are 60, 120 and 240 seconds, so a request is tried
  four times over about seven minutes. The observed bursts lasted three to six minutes.
- **The gate's budget covers the backoff.** `dependency-vulnerabilities` declares
  `timeout_seconds = 1200`, instead of inheriting the 600-second default.
- **Unobserved checks end evaluation early.** After the consistency check, a check whose verdict is
  `unknown` returns its native reason, the same reason its receipt names, so the decision and the
  receipt's gap agree. Only observed reports are parsed.

## Risks / Trade-offs

- A real outage now delays a failing audit by about seven minutes. A failing proof costs more than
  that.
- The stderr text is uv's own. If uv changes it, a reset is reported as `native_output_invalid`,
  which still fails closed. A test pins the current text.
