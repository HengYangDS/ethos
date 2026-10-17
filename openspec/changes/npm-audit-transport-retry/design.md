# Design

## Context

`npm audit --json` reports a failed advisory request as a JSON object with a `message` naming the request and an empty `error` member, then exits 1. The existing interpretation rejects that output as `native_output_invalid`, which correctly refuses to pass, but cannot distinguish a transport failure from a malformed report. npm's own fetch retry excludes POST requests, so its `fetch-retries` setting does not apply.

## Goals / Non-Goals

**Goals:**

- One dropped connection to the advisory endpoint no longer fails a complete proof.
- Every attempt remains in the receipt.

**Non-Goals:**

- Retrying findings, malformed reports, timeouts, spawn failures or the Python audit.
- Caching or reusing an earlier audit result, or modifying npm.

## Decisions

- **Classify the transport failure from npm's own JSON.** A nonzero exit whose JSON is exactly npm's audit error shape, with a `message` naming the bulk advisory request and no report fields, is `advisory_request_failed`. Matching stderr text was rejected because it is human diagnostics, not a contract.
- **Retry inside the existing owner and deadline.** At most three attempts with a short pause, each under the policy timeout. A wrapper around npm or a configuration change was rejected, because npm ignores retry settings for POST.
- **Keep the last attempt as the check and list the earlier ones.** The receipt gains `attempts` with each attempt's exit code, reason and stderr; the native verdict still comes only from the final attempt's own output.

## Risks / Trade-offs

- [A real outage costs up to three attempts before failing] → The pause is short and every attempt stays within the existing timeout, so the gate still fails with the same reason.
- [npm changes its error shape] → The classification falls back to `native_output_invalid`, which fails closed as before.
