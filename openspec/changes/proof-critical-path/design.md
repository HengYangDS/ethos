# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 2.12, 2.13, 2.14, 9.1, 9.2, 9.3 against their original acceptance conditions.
- Finish task 9.4, the contended admission that the archived design names for its host-contention risk.
- Finish task 9.5, which ends a queued proof that could no longer land.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.
- **Admit a full proof by repository slot, then host load.** Before any gate runs, a full proof takes the proof slot in the Git common directory, then waits until the 1- and 5-minute load averages are both within `ETHOS_PROOF_HOST_LOAD_LIMIT` (default half the CPUs, `0` for the slot alone); after one hour it ends with `proof_admission_contended`. The 5-minute average keeps a short lull between local CI jobs from admitting a proof into load that returns. The slot serializes full proofs across every worktree of a repository, and the load average covers local CI virtual machines and other repositories without naming their processes. A longer test timeout, a retried test or a smaller test surface was rejected, because the quality specification forbids each.
- **End a stale lane's proof at admission.** Landing requires the candidate in the lane's history, and a queued proof starts only after an earlier one ends, which is when that lane lands. So admission checks a Work Lane at start and at every poll, and ends its proof with `candidate_base_stale` and the refresh command before any gate runs. Other checkouts, and clones without the candidate branch, are not judged. A recheck at completion was rejected: a pass is still a true proof of that exact head, and landing already reports the stale base.
- **Reuse immutable reads within one command.** An object named by its full ID cannot change, so one application operation reuses its first successful read, and the running build is observed once. Refs, abbreviated names, the index, the worktree, configuration-dependent output and failed reads stay fresh. A cache that outlives the command was rejected, because nothing would bound when a ref-dependent answer goes stale.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [Load rises after admission, from work that does not take the slot] → Admission prevents starting into contention only; cutting per-test cost (2.13, 9.1) widens the headroom that remains.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
