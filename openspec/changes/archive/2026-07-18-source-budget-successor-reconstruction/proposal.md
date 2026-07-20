## Why

The previous source-budget Work Lane is semantically complete but diverged from the current candidate train. Its governed replay has a real content conflict in the debt ledger and bounded-reader surfaces; replaying historical parity projections would require skipping stale generated evidence. ETHOS therefore needs a candidate-based successor reconstruction that preserves current candidate behavior while restoring the strict source-budget lifecycle.

## What Changes

- Port the strict source-budget contract, schema, inventory adapter, configuration admission, and proof reducer onto the current `candidate/dev` baseline.
- Preserve candidate-owned bounded-reader, coordination, schema, and test semantics rather than replaying their older copies from the stale lane.
- Reconstruct the debt ledger as a current governance decision: retain candidate additions, settle the measured 100-line bounded-retirement record, require registered ISO waves and expiries, and keep baseline and terminal limits unchanged.
- Record one successor-only rollover of inherited active July 17 waves and matching expiries to July 18 after the candidate train advanced during reconstruction; it preserves every record ID, expected deletion, allowance, aggregate cap, baseline, and terminal limit.
- Regenerate claim, parity, proof, and archive evidence only after the successor head is verified.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=source-budget-successor-reconstruction; reuse=extend; change=modify; facet:lifecycle=authoring,validation,proof; facet:surface=policy,schema,config,cli,test,evidence; facet:authority=source,schema,openspec,evidence

## Impact

- `.ethos/rules.toml`, source-budget contracts/adapters/reducers, command registry, schemas, focused tests, quality documentation, OpenSpec, claims, and evidence.
- No new dependency, raw ref movement, force push, remote publication, baseline reset, terminal-limit change, or debt-cap increase.

## Out Of Scope

- Settling a debt record whose named deletion has not occurred.
- A second lifecycle rollover, a baseline reset, or an allowance/cap increase.
- Replay of predecessor parity, proof, claim, chronicle, or archive output as successor evidence.
- Candidate integration, accepted-root closeout, remote publication, or hosted CI success claims before HEAD-bound proof.
