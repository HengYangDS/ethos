# Proposal

## Why

`api.osv.dev` resets connections in bursts that last minutes. Several were observed on the host
and the CI guest on 2026-11-05 and 2026-11-06, recovering after three to six minutes. The audit
cannot ride them out:

- `uv audit` retries three times within seconds, then exits with an error and no output;
- ETHOS retries only npm's failed advisory request, pausing two seconds;
- acceptance then parsed the empty Python output as JSON and reported
  `finding_identity_unavailable`, a finding-identity problem that did not exist.

GitLab verify jobs 65914 and 65919 failed this way, and register rows 17 and 25 record the class.

## What Changes

- A Python audit that exits with an error, writes no report and names a failed advisory request is
  classified as `advisory_request_failed`, as npm's already is.
- Both ecosystems retry a failed advisory request with a bounded backoff of 60, 120 and 240
  seconds, long enough to outlast an observed burst. Every attempt stays in the receipt.
- Acceptance reports a check that observed nothing by its native reason, for example
  `advisory_request_failed`, instead of parsing its empty output.
- The dependency audit gate declares a 1,200-second budget, which fits the backoff.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the native dependency audit rides out advisory request bursts and reports an
  unobserved ecosystem by its native reason.

## Impact

- `tools/ci/dependency_audit.py`, `src/ethos/repository/policy/quality/dependency_acceptance.py`,
  `system/repository-gates.toml` and their tests.
- Out of scope: the advisory sources themselves, and the GitLab guest's network.
