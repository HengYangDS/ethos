## Why

ETHOS had two evolution ledger surfaces: `docs/governance/evolution-ledger.toml`
for hypotheses and `evolution/ledger.toml` for typed evolution records. That
violated SSOT and made docs act as a data store.

## What Changes

- Make `evolution/ledger.toml` the single repository-truth evolution ledger.
- Keep `docs/governance/evolution-campaign.md` as explanatory documentation only.
- Route campaign hypotheses, schema validation, audit requirements, and assistant
  context to the same ledger path.

## Capabilities

- `repository-governance`: subject=evolution-ledger-ssot; reuse=extend; change=modify; facet:lifecycle=runtime,validation; facet:surface=evolution,docs,cli,schema; facet:authority=source,schema,test

## Out Of Scope

- No new evolution ontology beyond the existing ledger/campaign model.
- No remote publication or hosted-provider workflow.
