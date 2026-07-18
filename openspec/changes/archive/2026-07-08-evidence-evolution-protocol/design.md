## Context

The official OpenSpec boundary is `repository-governance` plus `quality`. The
repo-local product boundary is the existing kernel chain:
`Change -> Evidence -> Claim -> Chronicle -> Evolution`. Evolution is not a
new memory center; it is the structural ledger for hypotheses and reviewed
change records.

## Design

Keep the existing physical roots: `evidence/claims`, `evidence/chronicle`,
`evidence/parity`, and `evolution/ledger.toml`. Strengthen the protocol between
them instead of adding directories.

`evolution_report` now validates two small invariants:

1. Active hypotheses must cite resolvable proof, review, and decision refs.
   Proof refs may be known ETHOS command references; review and decision refs
   must be repository paths.
2. Non-campaign evolution entries must cite at least one evidence ref and one
   decision ref, and those refs must exist.

`quality evidence-freshness` remains the single freshness read model. It now
combines claim digest/head checks with evolution protocol checks and enters the
default proof graph as a trust-bearing governance gate after `claims`.

## Alternatives

- Adding `evidence/evolution/` was rejected because it would create another
  proof location.
- Adding a separate `ethos evolution validate` command was rejected because the
  existing quality freshness surface already owns this question.
- Executing proof refs during freshness checks was rejected because freshness is
  a read model; executed proof remains `ethos prove --execute`.

## Proof Strategy

- Unit tests cover unresolved refs, missing entry bindings, schema enforcement,
  default gate membership, and CLI payload shape.
- `ethos quality evidence-freshness --json` proves the current ledger has no
  required gaps.
- OpenSpec validation proves the carrier and canonical specs.
- Full local CI and head-bound executed proof must pass before land.
