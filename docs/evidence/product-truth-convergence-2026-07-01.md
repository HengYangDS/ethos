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
  available through `ethos self audit`, `ethos self openspec`, and full proof.
- Internal ETHOS JSON gates now run in-process through the local runner.

## Performance Baseline And Improvement

Before optimization, full pytest reported `135 passed in 118.54s`; the slowest
tests repeatedly executed OpenSpec through full self-audit. `ethos prove --json`
measured about `8.85s` and `ethos report --json` about `8.68s`.

After optimization, focused measurement showed:

- `ethos prove --json`: about `0.11s`.
- `ethos report --json`: about `0.18s`.
- `ethos self audit --json`: about `8.62s`, preserving the deep official
  OpenSpec validation path.

## Verification Commands

Final verification for this batch is recorded in the closeout response. The
required gates include focused pytest, Ruff, OpenSpec validation, CLI smoke,
and `uv build --all-packages`.
