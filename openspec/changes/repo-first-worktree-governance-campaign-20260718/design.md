## Context

ETHOS already treats a Work Lane as the normal mutation boundary and OpenSpec as the change carrier, but campaign closeout aggregates every campaign. That aggregation makes a truthful closeout for a new bounded program impossible while the unrelated terminal-productization campaign remains active. The workstation portfolio also contains foreign and unbound lanes; neither shared host nor shared developer establishes shared lifecycle authority.

## Goals / Non-Goals

**Goals:**

- Create a dedicated, strict-serial campaign with one active bootstrap step and explicit future independent steps.
- Make campaign closeout selection explicit, read-only, schema-compatible, and observable in the output envelope.
- Bind bootstrap scope to an active claim, OpenSpec carrier, dated Chronicle, and future local-closeout evidence.
- Preserve the repo-first directory grammar: `<repo>`, `<repo>-worktrees/<date>-<task>`, and `<repo>-records/{.staging,evidence,recovery}/<timestamp>-<purpose>`.

**Non-Goals:**

- Do not enact any worktree cleanup, move, recovery, records creation, branch deletion, remote action, or process control in this slice.
- Do not treat the campaign as a shared mutable workspace or a substitute for per-lane proof and closeout.

## Decisions

1. **Dedicated campaign, not terminal-productization extension.** The bootstrap declares `repo-first-worktree-governance-v2` with a serial chain. This prevents unrelated productization steps from becoming dependencies or evidence for worktree governance.
2. **Bounded closeout selection.** `ethos campaign closeout --campaign <id>` passes the selector to the campaign report. The output records the requested selector and only evaluates selected campaign manifests for the campaign package and local readiness.
3. **No implicit authority transfer.** Git remains authoritative for refs/history/registration; ETHOS remains authoritative for policy, ownership, receipts, and gates. The campaign is an orchestration record only.
4. **Frozen topology, later mechanics.** Directory grammar and dirty-state recovery order are contractual now; capture, sealing, deletion admission, and retirement are separately implemented later to avoid a bootstrap that claims unsafe mechanics as done.

## Risks / Trade-offs

- **Selected closeout can hide unrelated campaign gaps if used carelessly** → the selector is explicit and returned in output; unselected campaigns are not asserted healthy.
- **Manifest plans can look like execution** → only the first step is active; all remaining steps stay planned and cannot authorize mutation.
- **Future implementation may outgrow the frozen grammar** → topology changes require a new governed change rather than ad hoc directory additions.

## Proof Strategy

Run focused campaign CLI and schema regressions, strict OpenSpec validation, lifecycle validation, claim validation, and a HEAD-bound local proof after committing. The final Chronicle records exact commands, the committed head, and the local-only boundary. The campaign’s first step becomes terminal only after candidate land, accepted-root local closeout, archive, and owned-lane retirement.
