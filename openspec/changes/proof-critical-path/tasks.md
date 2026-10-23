# Tasks

## 1. Measurement and Critical-Path Targets

- [ ] 1.11 Requalify the converged source within 900 seconds: p90 over at least five successful complete proofs and one exact-source proof of its installed package, each including preparation, every required gate and cleanup. Archived 1.9 stays complete; failed proof artifact `1aca729d12e47f7e155b954c52fa19dd6ab5f880148172656f34989f412de415`; leaf evidence at signed source `c6187cc5f` (`build/evidence/quality/{effect-profile-batching,commit-policy-observation}/manifest.json`).

## 2. Invocation-Scoped Facts and Proof Reuse

- [ ] 2.12 Share exact-source intent compilation within each proof query; retain fresh queries, archive withdrawal, contradictory evidence and per-effect admission, then measure the native release consumer before delivery.
- [ ] 2.13 Bind native typed object frames and exact set selection at their owners; remove redundant root hashing and ref probes, then verify unchanged set, fresh membership, faults and native release cost before delivery.
- [ ] 2.14 Observe release application once under its existing operation lock; preserve effect-time checks, lock contention, drift, refusal and interruption recovery, then measure the native release journey before delivery.

## 9. Startup and Structural Simplification

- [ ] 9.1 Resolve native startup and repeated observation costs at their owners.
- [ ] 9.2 Implement the highest-impact bounded repair with falsifying regressions.
  - [x] 9.2.1 Check each formatter's selected files in native runs instead of one process per file. `source-format` spent 81 s rendering ETHOS's 1020 files one at a time, and its CPU reservation kept `unit-architecture` from starting until it ended; inside the merge-selection journeys it ran in every fixture proof, so one of them reached the 240 s timeout on the ARM runner at `424d0e7f5`. Prettier, Ruff and Taplo now run their check mode once per configuration over chunks of real paths; a file a clean run leaves unchanged keeps its bytes, and every other file, including a file Prettier lists as drift, renders alone as before. Paths with pattern characters, Prettier inputs under an ignore carrier or a skipped directory, and Taplo policies that select paths stay per-file. Done when a clean selection launches the same native runs at any size and listed drift renders only its file (`tests/unit/adapters/gates/test_source_format_batching.py`), and batched and per-file postimages agree on ETHOS and six adopters (`build/evidence/proof-critical-path/9.2.1-format-batch-check/`; ETHOS 8.7 s against 99.5 s).
- [ ] 9.3 Verify equivalent results, reduced work, isolation and cleanup.
- [x] 9.4 Admit a full proof under measured host contention through the existing proof owner, so a concurrent proof or a local CI pipeline delays admission instead of failing gates by timeout; verify that a reproduced contended run times out no gate and an uncontended run is not delayed. Evidence: under the 1- and 5-minute rule, the proof of `46afaa19b` waited 616 s from a load of 27.8 and passed 35 of 35 gates without a timeout; the proof of `2a6da8e83` was admitted after 0 s at 6.4.
- [ ] 9.5 End a Work Lane's full proof at admission with `candidate_base_stale` and the refresh command once its candidate is no longer in the lane's history, at start or while waiting, so a queued proof that could no longer land runs no gate; verify that other checkouts and clones without the candidate are not judged, and observe a queued proof that ends this way after another lane lands.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
