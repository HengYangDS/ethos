## Why

The compression program needs many locally proven OpenSpec Changes before it can
make one coherent external release. Treating every Change as a remote-publication
boundary spends most execution time in provider closeout and wrongly turns
per-Change source growth into a failure, even when the declared campaign ends in
a larger net deletion.

## What Changes

- Add a campaign publication mode whose `campaign_terminal` value makes a
  campaign, rather than an individual Change, the remote-publication boundary.
- Derive terminal readiness from archived/retired campaign steps plus the global
  source-budget terminal targets and settled temporary compression debt.
- Add explicit `campaign_terminal` budget enforcement so declared temporary
  campaign debt may support local iterations without bypassing debt lifecycle
  or final terminal-budget enforcement.
- Bind that enforcement mode to exactly one external `campaign_id`, validate
  Campaign TOML against the tracked JSON Schema at read time, and fail closed on
  malformed publication declarations.
- Add the honest `archived` pre-land step state required by the existing
  archive-before-land lifecycle.
- Block protected remote pushes while an active `campaign_terminal` campaign is
  not terminal, while retaining normal Work Lane, candidate, and accepted-root
  local closeout.
- Return stable action identifiers from the domain projection and resolve their
  commands through `system/commands.toml`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=campaign-terminal-publication-boundary;
  reuse=extend; change=modify; facet:lifecycle=campaign,publication,closeout;
  facet:surface=manifest,read-model,hook,cli,openspec;
  facet:authority=source,test,schema,openspec,claim. Campaign terminal state
  SHALL gate external protected-ref publication without making temporary
  campaign-local compression debt a per-Change closeout blocker.
- `quality`: subject=campaign-terminal-source-budget-enforcement; reuse=extend;
  change=modify; facet:lifecycle=validation,closeout; facet:surface=schema,cli;
  facet:authority=source,test,schema,openspec. Campaign-terminal enforcement
  SHALL preserve policy and debt-lifecycle validation while deferring current-
  size and terminal-target enforcement to campaign closeout.

## Impact

- Campaign manifest schema and the global declarative-compression campaign
  declaration.
- Source-budget schema projection, command action registry, Campaign read model,
  campaign-closeout projection, and pre-push admission.
- Focused campaign, schema, and push-admission regressions.

## Out Of Scope

- Remote mutation, provider-specific GitLab/GitHub API calls, a second workflow
  engine, source-budget baseline resets, or a compatibility publication path.
