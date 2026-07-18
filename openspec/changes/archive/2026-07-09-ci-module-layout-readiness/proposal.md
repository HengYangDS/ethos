# CI Module Layout Readiness

## Why

Local CI caught a layer violation after enterprise-readiness code landed:
`ethos.repository.policy.readiness.enterprise` imported domain and adapter
modules. That made repository policy a hidden orchestration layer and weakened
the import-linter contract that keeps ETHOS's terminal package architecture
honest.

## What Changes

- Move the enterprise-readiness aggregator from repository policy into
  `ethos.domain.readiness.enterprise`, where cross-check orchestration belongs.
- Keep repository policy modules below domain and adapter layers.
- Preserve the public CLI command `ethos quality enterprise-readiness --json`.
- Remove the obsolete repository readiness package instead of leaving a
  compatibility facade.

## Capabilities

- `quality`: subject=ci-module-layout-readiness; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,ci,test,openspec; facet:authority=source,test,quality-gate,openspec

## Out Of Scope

- No import-linter exception or baseline increase.
- No new command plane or readiness truth store.
- No remote/hosted CI claim.
