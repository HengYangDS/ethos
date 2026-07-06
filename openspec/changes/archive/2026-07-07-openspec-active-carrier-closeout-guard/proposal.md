## Why

ETHOS could land and close out a change while its OpenSpec carrier remained in
`openspec/changes/` as an active change when its task list was not fully checked.
The old guard only blocked completed active changes, so an in-progress carrier
could leak into candidate or accepted-root truth.

## What Changes

- Treat active OpenSpec changes on `candidate` and `accepted_root` roles as
  blocking repository-audit gaps.
- Keep active OpenSpec changes legal in Work Lanes where authoring happens.
- Archive the previously leaked `evidence-topic-scoped-chronicle` carrier.

## Capabilities

- `repository-governance`: subject=openspec-active-carrier-closeout-guard; reuse=extend; change=modify; facet:lifecycle=validation,archive; facet:surface=openspec,cli,test; facet:authority=source,test,openspec

## Out Of Scope

- No new OpenSpec command plane.
- No provider-specific archive automation.
