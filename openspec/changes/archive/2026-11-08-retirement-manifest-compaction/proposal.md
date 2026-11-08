# Proposal

## Why

A reviewed abandonment keeps every node of the reviewed worktree inline in its request, and its
terminal receipt embeds the request again, so each such retirement writes the complete manifest
twice and keeps both copies for as long as the store keeps its records. On 2026-11-08 the Git-common
store held 3.4 GiB of lane retirement requests and 3.0 GiB of their receipts; all 212 requests with
reviewed content carried their manifests inline, the largest 57 MB for 178,100 nodes. The store
retention design (the archived `rc-plan` Appendix D) compacts them before the verb that retires old
records, which follows as its own Change.

## What Changes

- A reviewed request keeps its root, index and a manifest reference: the digest and size of a
  content-addressed manifest file and per-root totals of its directories, files, symlinks and file
  bytes. The manifest file holds every reviewed node and is written before the request.
- Admission and removal load the manifest by digest; a missing or altered manifest refuses with
  `lane_retirement_manifest_missing` or `lane_retirement_manifest_mismatch`, which select a fresh
  content review as content drift does.
- After the terminal receipt, the operation deletes its manifest unless another request without a
  terminal receipt binds it; a failed deletion is reported, not raised.
- A request that still carries its nodes inline no longer validates; its recovery continues through
  a fresh admission derived from its coordinates instead of an empty next action.
- The preview's review summary names the manifest file and counts its nodes from the totals.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: the reviewed manifest is kept apart from its request and receipt, bound
  by digest, until the operation is terminal; an inline request continues through a fresh
  admission.
- `command-plane`: a missing or altered manifest selects the same fresh content review as reviewed
  content drift.

## Impact

- `src/ethos/contracts/retirement.py`; in `src/ethos/adapters/mutation/lane_retirement/`, the new
  `manifest.py` and `inline.py` and the changed `linked_effect.py`, `operation.py`,
  `continuation.py` and `abandonment.py`.
- The lane retirement tests under `tests/unit/lanes/retirement/`, the CLI retirement tests in
  `tests/unit/cli/test_lane_retirement.py` and the scenario support in
  `tests/support/lane_scenarios.py`.
- Requests and receipts written before this Change keep their bytes; the retention verb retires them
  later. No adopter changes a file.
