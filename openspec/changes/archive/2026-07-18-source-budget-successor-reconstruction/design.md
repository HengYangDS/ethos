## Context

The original source-budget Lane was based on commit `0a4ea453…`; the successor began from `candidate/dev` at `34ffde96…`, which independently evolved bounded foreign-lane readers and debt records, and candidate advanced to `bbae6a43…` during reconstruction with closeout-verifier work. A controlled replay reproduces six real content conflicts in the first source-budget commit, followed by stale generated parity projections. The candidate version is the authority for bounded-reader behavior; the source-budget implementation is absent from candidate and must be reconstructed.

## Goals / Non-Goals

**Goals:**

- Land a strict, schema-backed source-budget lifecycle on the current candidate baseline.
- Preserve candidate bounded-reader semantics and candidate-only debt records.
- Keep the immutable baseline and terminal limits unchanged while settling the measured 100-line bounded-retirement record.
- Rebuild head-bound proof, claim, parity, and archive evidence from the successor head.

**Non-Goals:**

- Do not rewrite historical ownership or assert historical provenance for inherited symbolic fields.
- Do not use `ours`/`theirs`, `git rebase --skip`, raw ref moves, force push, or stale parity as proof.
- Do not land or retire the predecessor Lane until successor closeout evidence explicitly supports it.

## Decisions

1. **Candidate-first topology.** Start a new owned Work Lane from current `candidate/dev`. This avoids replaying stale generated evidence and keeps newer bounded-reader code, schema, and tests intact.

2. **Resolved-tree migration source.** Port only the candidate-plus-source-budget net tree produced by the bounded diagnostic replay. That tree successfully passed the normal Git hook before reaching generated parity; it is a source for reviewed content, not acceptance evidence.

3. **Debt ledger reconstruction and one-time rollover.** Normalize inherited records with explicit UTC-date waves and expected deletion fields. Retain the two candidate-only records with their identifier-derived July 18, 2026 commitments, preserve their allowances, and retain the candidate cap discipline. The resulting active aggregate is 7827: the previous 6926 migrated total plus 125 and 776 candidate records; it is 100 below candidate's 7927 because bounded-retirement was measured and settled. Because the candidate train advanced while reconstruction was still unproven, eight inherited active waves and seven matching July 17 record expiries roll once to July 18. The rollover neither increases an allowance or cap nor rewrites an ID, expected deletion, baseline, terminal limit, or settlement. Rejected alternatives are changing the process clock, silently accepting an expired ledger, increasing the cap, or marking unperformed deletion as settled. Review the rollover before any later extension or closeout.

4. **Evidence is regenerated, not replayed.** Old parity, proof, claim, and archive outputs remain historical in the predecessor Lane. The successor generates new evidence only after source, tests, and ledger are clean.

## Risks / Trade-offs

- **Candidate can advance during reconstruction** -> re-check HEAD before each mutation and use governed refresh-base if needed.
- **Debt commitments are time-sensitive** -> use the source-budget UTC provider and keep all dates explicit; the one-time July 18, 2026 rollover is future relative to July 17, 2026 and must not be extended again without a new decision.
- **Foreign lanes add advisory noise** -> retain observe-only boundaries; they do not authorize mutation or cleanup.
- **Long parity/proof processes can appear stalled** -> run only from a clean stable head with PID, timeout, and post-run evidence checks.

## Migration Plan

1. Create a successor OpenSpec carrier and add a failing source-budget contract test.
2. Port the reviewed candidate-plus-source-budget implementation, preserve candidate-owned reader semantics, and reconstruct the ledger with the documented one-time rollover.
3. Run focused tests, source-budget/schema/config gates, and full executed proof on a stable HEAD.
4. Bind a new successor claim, generate parity evidence once, archive the active Change, land to candidate, close out accepted roots, and only then evaluate predecessor retirement.
