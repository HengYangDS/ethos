# Design

## Context

See [proposal.md](proposal.md).

- **The walk.** Reclamation retains a generation when a fresh observation refers into it (PDC 424-433). For the process listing, `_native_path_prefixes` walks each absolute path one component at a time and records every prefix that exists. A reference inside a generation therefore records the generation's own directory before the walk reaches the leaf.
- **The race.** Each step checks existence, then calls `resolve(strict=True)`. The listing covers the whole host, so other processes create and delete those paths while the walk runs. A deletion between the two calls raised `FileNotFoundError`, and reclamation deferred.

## Goals / Non-Goals

**Goals:**

- A deletion between the check and the resolution has the same effect as a deletion before the check.
- Every other unknown observation stays fail-closed.

**Non-Goals:**

- Changing which paths are observed, or observing open files and working directories.
- Retrying the walk.

## Decisions

- **One helper checks and resolves.** It returns the resolved path, or nothing when the path is absent. `FileNotFoundError` for a path that is no longer present means it was deleted after its check: an observed absence.
- **A dangling symbolic link stays unknown.** It raises the same error, but it is still there, so reclamation defers as before. Permission errors and `NotADirectoryError` also stay unknown. Invalid command suffixes (`ENAMETOOLONG`, `EINVAL`) stay absent, as before.
- **Rejected: treating every resolution `OSError` as absent.** That would hide the permission and filesystem faults that the contract treats as unknown.
- **Rejected: retrying the walk.** On a host with constant churn a retry can defer again, and it adds no fact that the observed absence does not already give.

## Risks / Trade-offs

- [A process still runs from a generation after a path it names was deleted] → Its walk still records each existing directory above the deleted component, including the generation, so the generation is retained. A deletion before the check already behaved this way.
