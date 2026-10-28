# Proposal

## Why

Every source Change pays for two complete proofs: `lane archive-change` refuses to archive until the pre-archive head is proved, and landing then requires a proof of the archived head. The two proofs take 61 to 64 percent of local delivery time (design revision 5.1, decision D1), and only the second one reaches accepted history.

The first proof has no separate consumer. Landing already requires the passing proof of the exact archived head (`landing.py`), and archive already validates its actual postimage natively before the commit. What the first proof bought was a way back: once archived, a lane whose code fails cannot be edited, because its write scope is only the archive effect's paths. Nothing returns an archive whose proof fails, so the order "prove, then archive" was the only safe one.

The `--execution-root` proof carrier exists only for that order. It proves the pre-archive head in a second worktree while an official archive is staged in the lane (`2026-09-26-proof-execution-carrier`).

## What Changes

- **Archive needs no proof.** `lane archive-change` admits a completed Change at the exact Work Lane head without a pre-archive proof. Native validation of the actual postimage before the commit, the Lease, and the completed-Change checks stay. The archive reports `pending_verification` with the archived head's proof as its continuation.
- **A failed proof returns through compensation.** `lane archive-change --compensate` returns an archive commit that has not landed to its exact pre-archive head through one attested, Lease-bound compare-and-swap, and restores the index and worktree. The author fixes, commits and archives again. An interrupted compensation completes when it is repeated.
- **The proof execution carrier is retired.** `ethos prove` no longer accepts `--execution-root`. A staged archive is committed by `archive-change` and proved in the clean lane.
- **Specs.** The repository-governance requirements on archive completion and explicit archive selection are restated, compensation is added, and the two carrier requirements are removed.
- **Documents.** The archive passages in `runner-and-mutation.md` and `command-plane.md`, the release guide and the governance Skill map state the one-proof route. Two outdated statements in `runner-and-mutation.md` are corrected: the runner is `LocalGateRunner`, and landing copies no proof record into the candidate worktree.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: archive needs no pre-archive proof, an unlanded archive can be compensated, and the proof execution carrier is removed.

## Impact

- A source Change needs one complete proof instead of two. Delivery-inclusive Changes that land with an active Change still prove that head, and its archive simulation still runs.
- `python_product` falls by about 70 effective lines: the carrier and the precondition are removed, and the compensation is added in its own module.
- This Change itself archives with its own lane code, so it already uses the one-proof route. Adopters and hooks get the new route with the next release.
