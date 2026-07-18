---
subject: ethos:all-work-lanes-convergence-replay-20260718
role: plan
state: active
relations:
  implements: all-lanes-convergence-replay-20260718
  supersedes_execution_of: all-lanes-convergence-implementation-20260716
---

# All Work Lanes Convergence Replay — 2026-07-18

Status: active local Work Lane replay.

Purpose: complete the owned refresh-safety replay and its evidence-bound local closeout.

See also: [Mutation Rules](../../rules/mutation.md), [Evidence Rules](../../rules/evidence.md), and [OpenSpec Governance](../governance/openspec-governance.md).

## Objective

Complete the preserved current-contract safety intent in one clean successor
lane, then use proof-backed local lifecycle commands to advance only the owned
change. The complete Work Lane cohort remains an observation and resolution
program, not a permission to mutate every visible branch.

## Execution Sequence

1. Bind this Change, claim, lease, and exact baseline; use the repository-local
   runtime wrapper and an explicit holder actor for every mutating command.
2. Add and observe the three missing refresh regressions before implementation.
3. Implement the bounded signing/snapshot/detached-replay/CAS path; keep all
   projection recovery and failure cleanup fail-closed.
4. Recompute a compact all-lane matrix from fresh status immediately before any
   resolution decision. Preserve dirty, unbound, missing-lease, and
   foreign-owned state until its exact native path is admitted.
5. Complete strict Change lifecycle, required parity, source budget, focused
   and full proof. Land and accepted-close only the stable owned head.
6. Invoke holder-bound or accepted exceptional resolution per exact lane only;
   report any owner, remote, hosted, or product limitation that prevents local
   closeout instead of implying success.

## Anti-stall Controls

- Run ETHOS through `tools/ci/scripts/run-ethos-lane.sh`, not the globally
  installed executable, so the runner binds to this Work Lane rather than the
  protected root.
- Prefix owned mutation admission with
  `ETHOS_ACTOR=agent:codex:thread:root` so lease-holder identity is explicit.
- Capture long command output and exit codes to a bounded temporary evidence
  path, then poll the result; do not infer terminal completion from a tool UI.
- Keep foreign branches and pre-existing recovery material read-only unless a
  fresh exact lifecycle command admits an effect.

## Completion Boundary

Local closeout requires a fresh committed HEAD with passing required gates,
parity where required, executed proof, candidate land, and accepted-root
closeout. Remote publication and hosted execution remain separate, unclaimed
evidence planes.
