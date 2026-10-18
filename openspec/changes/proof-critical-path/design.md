# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 2.12, 2.13, 2.14, 9.1, 9.2, 9.3 against their original acceptance conditions.
- Finish task 9.4, the contended admission that the archived design names for its host-contention risk.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.
- **Admit a full proof by repository slot, then host load.** Before any gate runs, a full proof takes the proof slot in the Git common directory, then waits until the 1-minute load average is within `ETHOS_PROOF_HOST_LOAD_LIMIT` (default half the CPUs, `0` for the slot alone); after one hour it ends with `proof_admission_contended`. The slot serializes full proofs across every worktree of a repository, and the load average covers local CI virtual machines and other repositories without naming their processes. A longer test timeout, a retried test or a smaller test surface was rejected, because the quality specification forbids each.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [Load rises after admission, from work that does not take the slot] → Admission prevents starting into contention only; cutting per-test cost (2.13, 9.1) widens the headroom that remains.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
