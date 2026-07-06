---
subject: ethos:lane-collaboration-readmodel
state: proven
created: 2026-07-06
claim: lane-collaboration-readmodel
head: bcd994f2555e306ec4b2215bc469d7362f3dd3c7
---

# Lane Collaboration Read Model Evidence

## Claim

ETHOS exposes foreign Work Lanes as observable, current-actor observe-only
subjects. Visibility does not grant write, land, or retire authority; mutation
remains bounded by lane ownership, accepted handoff, or maintainer break-glass
evidence. The product contract also admits creative, destructive, or simplifying
changes when they produce provable net gain and retain rollback boundaries.

## Net gain

- Makes hidden multi-agent collision risk visible in `ethos status --json`.
- Adds machine-readable current actor capability to `foreign_work_lanes[]`.
- Keeps the design provider-neutral: assistant hosts and hosted forges are
  adapters, not truth centers.
- Preserves creative/destructive change capacity by requiring net-gain evidence
  instead of preserving inherited shape.
- Classifies the new `handoff_required` signal under the existing Change
  invalid-state category instead of adding a parallel taxonomy.

## Validation

- `ethos lane prewrite ... --editor-root "$PWD" --require-editor-root --json`:
  admitted tracked writes in `work/lane-collaboration-readmodel`.
- Focused tests: `5 passed` for foreign Work Lane status, CLI contract, and
  coordination edges.
- Regression tests for taxonomy and product docs: `2 passed`.
- Full test suite: `715 passed`, coverage `95.41%`.
- `run-python-lint.sh`: passed.
- `run-config-lint.sh`: passed.
- `run-shell-lint.sh`: passed.
- `quality_audit.py`: `ok=true`, no required gaps.
- `portfolio_audit.py`: `ok=true`, no required gaps.
- `ethos quality schemas --json`: `ok=true`, `state=clean`.
- `ethos openspec --lifecycle --json`: `ok=true`, `state=clean`.
- `ethos report --json`: `ok=true`, `score=16/16`, `governance_gap_count=0`,
  `parity_pending_count=0`.
- `ethos parity shadow --adopter generic --target . --execute --write-evidence
  --json`: `ok=true`, `state=matched`, no required gaps.

## Boundaries

This evidence does not claim a host message bus, automatic handoff, remote CI,
remote publication, or semantic conflict resolution beyond the repository facts,
status read model, tests, schemas, OpenSpec carrier, and executed proof.
