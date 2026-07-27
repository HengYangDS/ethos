---
subject: ethos:all-work-lanes-convergence-replay-20260718
role: plan
state: superseded
relations:
  implements: all-lanes-convergence-replay-20260718
  supersedes_execution_of: all-lanes-convergence-implementation-20260716
  superseded_by: ethos:terminal-governance-product-design
---

# All Work Lanes Convergence Replay — 2026-07-18

Status: superseded by the terminal-convergence campaign; retained as historical
planning context only.

Purpose: preserve the intent that the terminal campaign absorbed without
remaining an executable lifecycle plan.

See also: [Mutation Rules](../../rules/mutation.md), [Evidence Rules](../../rules/evidence.md), and [OpenSpec Governance](../governance/openspec-governance.md).

## Objective

The terminal campaign absorbed the refresh-safety intent. The complete Work Lane
cohort is now a fresh observation set, never reusable mutation authority.

## Execution Sequence

1. Bind the selected ChangeContract, Lease, and exact baseline; use the repository-local
   runtime wrapper and an explicit holder actor for every mutating command.
2. Add and observe the three missing refresh regressions before implementation.
3. Implement the bounded signing/snapshot/detached-replay/CAS path; keep all
   projection recovery and failure cleanup fail-closed.
4. Recompute a compact all-lane observation from fresh status. Preserve and
   block dirty, unbound, missing-lease, and foreign-owned state.
5. Complete strict Change lifecycle, required parity, source budget, focused
   and full proof. Land and accepted-close only the stable owned head.
6. Use only holder handoff, exact authorized Lease takeover, and linked
   `landed|superseded` lifecycle effects; report every remaining blocker.

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
