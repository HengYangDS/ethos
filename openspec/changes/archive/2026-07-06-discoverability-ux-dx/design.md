## Design

`ethos orient` is a reader projection over repository truth. It composes:

- `workspace_status(root)` for role, dirtiness, branch, candidate, Work Lane
  coordination, and foreign-lane capability.
- `scorecard_report(root)` for governance score, gaps, parity freshness, and
  scorecard-level next actions.

The packet is intentionally explicit about its boundary:

```text
kind = orientation
truth_boundary = repository-reader-view
mints_truth = false
source_payloads = [status, report]
```

The human form is short enough for a terminal first glance. The JSON form is
stable enough for agents to decide whether they may mutate, must observe, or
need to ask for handoff. The design follows repository nature: Git and lane facts
remain Git and lane facts; orientation only makes them visible.

## Net gain

- 显象: hidden role/capability/foreign-lane state is visible in one packet.
- 校度: write capability, landability, and observe-only boundaries keep separate
  measures.
- 转枢: the transition loop remains centered on status/plan/prove/land/publish;
  orient is not a new transition verb.
- 物遂其性: CLI, agents, docs, and future UI can project the same packet without
  owning truth.
