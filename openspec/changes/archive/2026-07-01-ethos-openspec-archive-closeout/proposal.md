## Why

OpenSpec closeout must finish as product lifecycle, not only as a manual
archive convention. The previous campaign lanes proved, landed, accepted-root
closeout-applied, and retired, but their OpenSpec carriers remained active
until this lane because ETHOS did not yet treat archive health as a closeout
gate.

## What Changes

- Add an ETHOS archive closeout report over official OpenSpec archive output.
- Make land and accepted-root closeout consume archive closeout gaps through the
  existing OpenSpec lifecycle package.
- Archive the already-closed campaign orchestration and OpenSpec product
  protocol carriers through the official OpenSpec archive command.
- Repair the one historical archive missing `.openspec.yaml` metadata.

## Capabilities

- `ethos-adapters`: subject=openspec-archive-closeout; reuse=extend; change=modify; facet:lifecycle=archive,validation; facet:surface=cli; facet:authority=source,test,openspec,evidence
- `ethos-repository`: subject=terminal-openspec-productization; reuse=extend; change=modify; facet:lifecycle=archive,closeout; facet:surface=docs; facet:authority=openspec,claim,evidence

## Out Of Scope

- This change does not make OpenSpec the public ETHOS command plane.
- This change does not generate adopter OpenSpec scaffold templates.
- This change does not implement hook-based write admission or release
  distribution evolution.
