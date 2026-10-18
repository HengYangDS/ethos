# Proposal

## Why

On 2026-10-17 three complete ETHOS proofs failed at `dependency-vulnerabilities` although the Python audit was clean and no npm finding existed. The npm audit request to the registry's bulk advisory endpoint failed on transport: a DNS failure, a dropped TLS handshake and a socket hang-up. npm never retries POST requests, and the bulk advisory audit is a POST, so one dropped connection fails the gate and every gate that depends on it.

## What Changes

- Repeat the npm audit observation a bounded number of times when, and only when, npm reports that the bulk advisory request itself failed and returned no audit report.
- Record every attempt in the dependency audit receipt, so a recovered transport failure stays visible.
- Leave findings, malformed output, other native failures and every policy decision unchanged.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. The dependency audit still requires complete, clean native evidence from both ecosystems; this changes how one observation is attempted, not what it must establish.

## Impact

`tools/ci/dependency_audit.py`, the native result interpretation in `src/ethos/repository/policy/quality/dependency_acceptance.py`, and their unit tests.
