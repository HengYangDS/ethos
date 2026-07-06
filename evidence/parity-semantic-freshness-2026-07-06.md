---
subject: ethos:parity-semantic-freshness
state: proven
created: 2026-07-06
claim: parity-semantic-freshness
head: fe9e6837305f4586bd4365545196112b47802022
---

# Parity Semantic Freshness Evidence

## Claim

Tracked shadow parity evidence binds both commit heads and the parity-relevant
semantic Git tree. Evidence-recording commits no longer stale themselves, while
later changes to parity-relevant source, contracts, OpenSpec, claims, rules,
skills, workspace policy, lockfiles, or governance docs still reopen parity
gaps.

## Net gain

- Removes an impossible fixed point: evidence no longer needs to predict the
  commit hash that will include itself.
- Keeps HEAD binding visible in provenance.
- Adds semantic tree freshness as a stricter witness than accepting arbitrary
  parent commits.
- Preserves parity as an early signal: real parity-relevant changes still stale
  evidence.
- Moves the parity-relevant path set into the parity module as the SSOT.

## Validation

- Focused parity tests: `57 passed`.
- `run-python-lint.sh`: passed with PLR0913 ratchet preserved at `37/37`.
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

This evidence binds the baseline commit that introduced semantic parity
freshness. The authoritative freshness witness for the final landed commit is
`evidence/parity/generic-shadow.json`, which may remain current across a later
evidence-only commit when the parity-relevant semantic Git tree is unchanged.

This evidence does not claim remote CI, remote publication, adopter-specific
domain parity, or semantic correctness beyond the shadow commands, tracked
parity evidence, tests, schemas, OpenSpec carrier, and executed proof.
