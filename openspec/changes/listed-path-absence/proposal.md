# Proposal

## Why

Generation reclamation reads the host-wide process listing and resolves every absolute path that a running command names, so that a generation still in use is retained. For each path it first checks existence, then resolves it.

- If another process deletes a listed path between those two steps, resolution raises `FileNotFoundError`. Reclamation then defers as though the observation were unknown, and removes nothing.
- A full proof on 2026-10-26 failed this way. `test_historical_runtime_observation_does_not_pin_an_executable_generation` removed nothing while other test workers were creating and deleting paths that their commands named. With the native `ps`, one listed path that keeps vanishing reproduces it: 73 of 81 reclamations deferred with `[Errno 2] No such file or directory`.

Under the Product Design Contract, unknown observations defer deletion (PDC 424-433). A path deleted after its check is not unknown. It is an observed absence, exactly like a path that was already absent at the check. Any proof can hit the race, for ETHOS and for its adopters.

## What Changes

- The observation walk treats a listed path deleted between its existence check and its resolution as absent.
- A dangling symbolic link, and every other resolution error, stays unknown and still defers reclamation.
- When the historical-observation test fails, it reports the whole result.
- The process-listing tests move into their own module, so that the retirement tests stay within the paradigm's size ceiling.
- A changelog entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: the requirement "Generation reclamation uses fresh operational facts" names a path deleted while it is observed as an observed absence.

## Impact

- Code: `src/ethos/adapters/repo/runtime/retirement.py`; tests in `tests/unit/adapters/repo/runtime/`: `test_retirement.py`, the new `test_retirement_listing.py` and its shared `support.py`.
- A listed path that resolves into a generation still retains it. `python_product` does not grow.
