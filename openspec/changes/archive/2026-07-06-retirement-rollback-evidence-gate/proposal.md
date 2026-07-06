# retirement-rollback-evidence-gate

## Why

External ETHOS must not accept embedded-backend retirement from profile state
alone. A repository could otherwise set `external_backend.state =
"retirement_ready"` while the rollback window remains only a narrative promise.

## What Changes

- Add a generic `[rollback_window]` profile evidence check to retirement
  readiness.
- Require a tracked evidence manifest once external ETHOS is the reversible
  default and embedded ETHOS is frozen.
- Require completed minimum scenarios for proof/report, Work Lane closeout,
  domain-gate planning, and assistant/playbook routing.
- Keep adopter-specific evidence in the adopter repository instead of adding
  adopter-named product directories.

## Capabilities

- `ethos-repository`: subject=retirement-rollback-evidence-gate; reuse=extend; change=modify; facet:lifecycle=adoption,retirement,validation; facet:surface=cli,docs,openspec,test; facet:authority=source,test,docs,openspec

## Out of Scope

- No alphasim-dmgr backend state is changed.
- No rollback-window evidence is claimed complete.
- No remote publication is performed while GitLab is unavailable.
