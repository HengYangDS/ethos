## Context

The historical Foundation carrier is archived at
`openspec/changes/archive/2026-07-19-budget-contract-v2-foundation-20260719`.
Its final successor HEAD is
`21b4ac47d22fca44155b8d79a0e9529f50f6e1d5`; its proof remains historical
evidence rather than proof for a later continuation HEAD.

That successor began from candidate
`4ddd805872ac5645617a5b290381cfd25c68464f`. Before it could land, candidate
advanced to `b90c409949eb37ae27967003c8fa98e97b78dcec`. Land reported
`candidate_base_stale`; the official refresh encountered a semantic conflict,
returned `refresh_base_failed`, and restored the old Lane clean.

The first continuation Lane therefore began at `b90c4099`, with holder
`agent:codex:thread:019f77ec-a00d-75e0-9ba3-47a00855b705`, lease
`lease:2ab06c73-f71b-45d4-902d-f6933ca14c19`, and claim
`budget-contract-v2-foundation-20260719`. While its no-fast-forward absorption
was being prepared, candidate first advanced to
`797e6e48dd8771cae840b3d796cad89db2dcc199` and then advanced again. These are
historical checkpoints, not a hard-coded future base. The continuation must
preserve the current merge, re-read the latest candidate at successor start,
and repeat the same candidate-first pattern rather than linearizing a
topology-bearing merge.

## Goals / Non-Goals

**Goals:**

- Preserve every useful predecessor commit through explicit merge ancestry.
- Keep the same episode claim while moving current authority to an active
  continuation carrier and current Chronicle.
- Preserve candidate configuration, quality-gate, and parity semantics, then
  regenerate all head-bound projections and proof.
- Correct the reviewed baseline replay and extraction-plan facts without
  modifying the historical archive or Chronicle.

**Non-Goals:**

- Implement Budget Contract v2 Tasks 2 through 10.
- Change v1 policy, reset its baseline, add allowance, extend expiry, or convert
  LOC into another metric.
- Claim candidate land, accepted-root closeout, remote publication, or hosted
  CI before their separate native transitions execute.

## Decisions

1. **Candidate-first successors.** Each continuation starts from the latest
   observed candidate and binds the existing episode claim. A stale predecessor
   Lane and every archived carrier remain observe-only.
2. **Fail-closed refresh.** A real semantic refresh conflict must abort and
   restore the expected clean head. Manual `rebase --continue`, `--skip`, raw ref
   movement, or history replacement is forbidden.
3. **No-fast-forward ancestry.** The continuation merge uses the candidate base
   as first parent and the predecessor head as second parent. The first merge
   must therefore retain `b90c4099` / `21b4ac47` as its exact parent order. If
   candidate advances again, a new successor starts from that new candidate and
   absorbs the completed topology-bearing continuation head as its second
   parent.
4. **Projection regeneration.** Candidate parity/config/gate projections win
   any merge conflict, but that selection marks parity stale. The resulting
   successor regenerates parity and executes proof for its own immutable HEAD;
   no historical receipt is reused as current proof.
5. **Superseding correction.** The current-v1 baseline replay is recorded as
   105060, net -282 ELOC, with JavaScript +1, YAML -282, and diagram -1 across
   933 governed files. Plans and the continuation Chronicle carry the
   correction; the historical archive and Chronicle are not edited.
6. **Boundary separation.** Archive, land, accepted closeout, local publication
   readiness, remote publication, hosted CI, and Lane retirement remain
   separately evidenced transitions.

## Risks / Trade-offs

- [Candidate advances during closeout] -> start another candidate-first
  successor and absorb the prior continuation head; do not rewrite history.
- [Parity chosen during conflict appears current] -> treat it as a candidate
  projection only and require a fresh generated receipt at the merged HEAD.
- [Historical wording remains inaccurate] -> preserve it as immutable history
  and make the superseding correction explicit in current truth carriers.
- [Long continuation chain increases topology] -> accept explicit ancestry over
  silent linearization; retire owned predecessors only after accepted ancestry
  proves absorption.

## Migration Plan

1. Complete the staged no-fast-forward merge and verify exact parent order.
2. Record the merge SHA, rerun admission, and commit the Chronicle/claim update.
3. Re-read the latest candidate immediately before successor creation (the
   first post-merge checkpoint was `797e6e48`), then start a fresh owned
   successor from that exact head and no-fast-forward absorb the completed
   continuation head.
4. Regenerate parity, run focused and changed-scope verification, and execute a
   HEAD-bound proof.
5. Complete and officially archive this Change, update the claim to the dated
   archive, refresh archive parity, and execute archive-HEAD proof.
6. Land to candidate, perform accepted-root closeout, report local publication
   readiness, and retire only the owned absorbed Lanes in dependency order.

Rollback before land is to leave candidate and protected roots unchanged and
preserve the owned continuation Lane for a later successor. Historical archive
records are never rolled back by editing them.

## Open Questions

None. A newly observed candidate movement is handled by the same repeatable
successor rule rather than by an ad hoc exception.
