# Design

## Context and boundary

This change extends the existing exceptional Work Lane resolution capability.
Tracked Chronicles remain the authority for exceptional action; `build/` stays
an ignored local-artifact projection. The product must make that projection
inspectable without turning it into a parallel truth store or a mutable global
index.

## Durable local receipts and inventory

After every successful resolution effect, ETHOS will validate and atomically
write one immutable receipt at
`build/artifacts/lane-resolution/receipts/<decision-digest>.json`. The receipt
will bind the decision, lane ref, observed head, observation digest, and, when
present, the recovery-package path and manifest digest. Per-decision files
avoid a shared append-only index and therefore avoid a new cross-agent write
hotspot.

`ethos lane resolution inventory --json` will derive a read-only view from the
receipt directory, package manifests, and any clear receipts. It reports a
package as retained, cleared, or unindexed; it never infers authority from an
artifact. Existing packages remain visible as unindexed manifests until an
explicit future reconciliation promotes more data.

## Retention and manual clear

`ethos lane resolution clear` will select exactly one package by decision ID.
It requires the current manifest SHA-256, a Chronicle containing
`lane_resolution/clear-preservation`, a non-empty reason, `--break-glass`, and
`--confirm-irreversible --apply`. It writes a separate clear receipt before
removing only the selected package directory. The original resolution receipt
remains as a small local history record; clearing never deletes a Chronicle or
Git truth. A changed or missing manifest fails closed.

## Source-bound runner bootstrap

The repository-owned `tools/ci/scripts/run-ethos-lane.sh` resolves the current
Git worktree, exports `UV_PROJECT_ENVIRONMENT=build/runtime/venv` and
`UV_CACHE_DIR=build/runtime/tool-cache/uv` when callers have not set them, and
runs `uv run --package ethos ethos ...`. It keeps the environment inside the
semantic runtime home and ensures the executable is built from the current
worktree. `ethos lane start` returns this exact bootstrap contract and a
copyable next action; it does not create a virtual environment as a side effect
of lane admission.

## Alternatives

- A single mutable JSON index was rejected because concurrent resolutions
  would share a write target and a lock protocol would become another local
  authority surface.
- A root `.venv` default was rejected for new lanes because it obscures the
  runtime owner and pollutes the repository root.
- Automatic retention expiry was rejected because recoverability is an
  evidence-bound maintainer judgment, not a cache TTL.

## Proof strategy and rollback

Focused unit and CLI tests prove receipt materialization, inventory states,
manifest-bound clear refusal, runner bootstrap output, and generated-artifact
topology. OpenSpec lifecycle validation, command/docs/schema checks, generic
parity, and HEAD-bound executed proof bind the final claim. Rollback is a
normal revert of tracked source and docs; retained packages are never removed
by rollback. The change makes no remote claim.
