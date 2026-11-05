# Proposal

## Why

The batch-2 integration head `8f94e39c3`, which joins `release-binary-scan`,
`adopter-tag-receipts`, `lease-holder-surface` and dev at `fa6ace8ec`, fails two architecture
tests. Each lane was correct on its own base; dev's rules arrived after them.

- `test_declared_timeouts`: `tools/ci/release_binary_scan.py` binds three literal waits (600, 1800
  and 120 seconds), so `tools/` holds 34 against the ratchet of 31. Dev requires every new wait to
  come from a declared parameter.
- `test_decision_records_preserve_complete_cross_change_rationale`: DR-0018 has four sections. Dev
  requires a fifth, `Evidence and Revisit`.

## What Changes

- The binary scan reads its waits from declared timeout parameters: `download` for the SBOM
  download, `gate` for the Grype scan and `request` for the lock read.
- DR-0018 gains its `Evidence and Revisit` section.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A wait's source and a decision record's section change no requirement, so `skip_specs: true`
applies.

## Impact

`tools/ci/release_binary_scan.py` and `docs/decisions/dr-0018-historical-artifact-attestation.md`.
