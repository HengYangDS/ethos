# Proposal

## Why

On 2026-11-10 readiness ran while local-install-smoke held the dependency audit's evidence
directory. The audit session refused correctly with `dependency_audit_in_use`, but it printed no
payload, so the gate parsed an empty stdout. Readiness then reported only
`Expecting value: line 1 column 1 (char 0)` as the gap, and the real cause appeared only in the
session's output. A refusal that names no gap fails closed but cannot be acted on.

## What Changes

- On contention the audit session prints one refusal payload: `command`, `state = "refused"` and
  the gap in `required_gaps` and `decision.reason`. Then it errors as before.
- `captured_dependency_acceptance` reads a refusal payload's reason as its own reason. Output that
  is not a JSON payload at all reads as `dependency_audit_payload_missing`, never as a parser
  message.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The gate's verdicts are unchanged; only the gap it names changes.

## Impact

`tools/ci/dependency_audit.py`, `src/ethos/adapters/repo/dependency_acceptance.py`,
`src/ethos/adapters/gates/runner.py` and two test modules under `tests/unit/ci/dependency_audit/`.
