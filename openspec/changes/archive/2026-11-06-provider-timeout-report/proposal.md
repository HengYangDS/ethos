# Proposal

## Why

A provider gate that returns after its deadline loses everything it observed. `provider_reports`
checks the deadline again after the provider returns, and on expiry raises a bare
`TimeoutExpired` that names the provider reference and holds no output. Its handler then records
the report as `{"verdict": "unknown"}`. On 2026-11-07 architecture-publisher's `node-behavior`
gate timed out this way: its result held only that empty report and a diagnostic with empty
streams, so no agent could tell whether the tests hung or were only slow.

## What Changes

- A provider that returns after its deadline keeps its report in the gate's result. The gate stays
  unknown with `gate_timeout:<gate>`, and the timeout diagnostic names the provider, its bound and
  its elapsed seconds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kernel`: a timed-out part keeps what it observed.

## Impact

- `src/ethos/adapters/gates/verification.py`.
