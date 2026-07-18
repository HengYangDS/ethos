## Why

The terminal productization work is larger than one Work Lane. Treating the
batch as a single lane hides ownership, OpenSpec scope, proof attribution, and
closeout progress. ETHOS already describes campaign as a long-running goal
container, but the command plane only exposes hypotheses and a generic local
closeout package.

## What Changes

- Add campaign manifests under `evolution/campaigns/<campaign-id>/campaign.toml`.
- Report campaign steps through `ethos campaign status --json`.
- Add a campaign package to `ethos campaign closeout --json`.
- Validate campaign manifests with `campaign.schema.json`.
- Record the terminal OpenSpec productization batch as a campaign made of
  consecutive OpenSpec-backed Work Lanes.

## Capabilities

- `ethos-repository`: subject=campaign-orchestration; reuse=extend;
  change=modify;
  facet:lifecycle=authoring,validation,archive; facet:surface=cli,schema,docs;
  facet:authority=source,schema,openspec,evidence,claim
- `ethos-cli`: subject=campaign-status-closeout; reuse=extend;
  change=modify;
  facet:lifecycle=validation,runtime; facet:surface=cli;
  facet:authority=source,schema,openspec

## Out Of Scope

- Do not implement every terminal productization lane in this change.
- Do not copy reference adopter Backlog or Mission vocabulary into ETHOS core.
- Do not make Work Lane presence itself promote claim or evidence truth.
