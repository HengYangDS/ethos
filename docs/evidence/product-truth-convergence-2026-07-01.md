---
subject: evidence:product-truth-convergence
role: evidence
state: active
relations:
  supports: ethos-product-truth-convergence
---

# Product Truth Convergence Evidence

This evidence records the ETHOS product-truth convergence batch.

## Scope

- Physical target product package homes were added for `ethos-core`,
  `ethos-contracts`, `ethos-repository`, `ethos-assistants`, `ethos-adapters`,
  and `ethos-test`.
- `ethos parity ledger`, `ethos parity gaps`, and `ethos parity shadow` were
  added as the executable capability parity control plane.
- Daily `ethos prove --json` and `ethos report --json` were moved to shallow
  OpenSpec self-audit mode while deep official OpenSpec validation remains
  available through `ethos self audit --mode deep`, `ethos self openspec`, and
  full proof.
- Internal ETHOS JSON gates now run in-process through the local runner.
- `ethos self audit` and `ethos self prove` now expose explicit `--mode
  shape|deep` UX. Daily gates use `shape`; release proof keeps `deep`.

## Performance Baseline And Improvement

Before optimization, full pytest reported `135 passed in 118.54s`; the slowest
tests repeatedly executed OpenSpec through full self-audit. `ethos prove --json`
measured about `8.85s` and `ethos report --json` about `8.68s`.

After optimization, focused measurement showed:

- `ethos prove --json`: about `0.11s`.
- `ethos report --json`: about `0.18s`.
- `ethos self audit --mode deep --json`: about `8.62s`, preserving the deep
  official OpenSpec validation path.
- Full pytest after the additional gate and test harness optimization reported
  `158 passed in 22.84s`.

## Verification Commands

Final verification for this batch is recorded in the closeout response and
includes focused pytest, full pytest with durations, Ruff, OpenSpec validation,
CLI smoke, and `uv build --all-packages`.
