## Why

ETHOS already keeps claims, chronicle records, parity evidence, and evolution
hypotheses in tracked repository truth, but the `quality evidence-freshness`
surface only checked claim digests. That left a small but important gap: a
structural evolution record could become narrative text unless its proof,
review, and decision references resolved back to repository truth.

## What Changes

- Extend the existing evidence-freshness gate so it reports both claim freshness
  and evolution-ledger protocol health.
- Require non-campaign evolution entries to bind evidence and decision refs.
- Require hypothesis proof, review, and decision refs to resolve as known ETHOS
  command references or repository paths.
- Include `evidence-freshness` in product and adopter default proof floors.

## Capabilities

- `repository-governance`: subject=evidence-evolution-protocol; reuse=extend; change=modify; facet:lifecycle=validation,proof; facet:surface=evidence,evolution,claim,chronicle,schema,cli,openspec; facet:authority=source,test,schema,docs,openspec,claim,evidence
- `quality`: subject=evidence-evolution-protocol; reuse=extend; change=modify; facet:lifecycle=validation,proof; facet:surface=cli,ci,schema; facet:authority=source,test,schema,docs,openspec

## Out Of Scope

- No new proof root, ledger, chronicle store, or command plane.
- No runtime execution of proof refs during freshness checks.
- No replacement of OpenSpec, claims, or chronicle with evolution records.
