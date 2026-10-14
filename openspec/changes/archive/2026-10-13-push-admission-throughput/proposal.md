## Why

Converging GitLab after the history repair failed twice on 2026-10-13. Custody Attestation 720737c7b83726d5 profiled the native pre-push hook on that input:

- It took 467 s, but `ethos publish` gives the push a fixed 120 s, so the push was cut off before the hook finished.
- `read_attestation_set` ran five times for 173 s. The selected set now holds 2,684 members and 280 MiB, mostly embedded custody manifests. Member validation reuse is bounded at 64 MiB of retained input, so every full read evicts what the previous read cached and nothing is reused.

The same reuse loss slows every proof, land and publication that reads the set more than once.

## What Changes

- Member validation reuse is bounded at 512 MiB of retained serialized input instead of 64 MiB, so a repeated read of today's set reuses validation. Each read still freshly observes membership, bytes and framing.
- The publication push deadline is a 120 s transfer allowance plus twice the admission just measured for that peer. The pre-push hook re-derives exactly that admission, so a range-dependent hook is no longer cut off by a constant.

## Impact

- Code: `src/ethos/adapters/repo/attestation_set.py`, `src/ethos/adapters/mutation/publication/execution.py`.
- Tests: `tests/unit/kernel/attestation_set/test_reuse.py` and a focused push-budget test.
- Specs: repository-governance gains one requirement for the publication push budget. The pure reuse requirement is unchanged.
