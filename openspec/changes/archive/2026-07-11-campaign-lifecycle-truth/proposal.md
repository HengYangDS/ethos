## Why

The terminal OpenSpec productization campaign records hooked write admission as
`active`, although its carrier is archived, every task is complete, and the
accepted history records its local closeout.  The campaign reader therefore
projects a false active lane and its strict-serial topology cannot detect the
contradiction.

## What Changes

- Reconcile the historical hooked-write-admission step with its accepted and
  candidate closeout heads and its dated Chronicle.
- Make campaign lifecycle validation distinguish an active OpenSpec change from
  an archived one, and require step state to agree with carrier and closeout
  state.
- Preserve an honest waiting state: a campaign may remain active with no
  active step while its next step is still planned.
- Expose the rule in canonical campaign-governance documentation and protect it
  with focused regression tests.

## Capabilities

- `repository-governance`: subject=campaign-lifecycle-truth; reuse=extend;
  change=modify; facet:lifecycle=validation,closeout; facet:surface=cli,docs,
  openspec,evidence,test; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- No implementation of the planned adopter OpenSpec scaffold or later campaign
  steps.
- No new campaign, lease, or lifecycle truth store.
- No hosted CI, remote publication, or foreign Work Lane mutation.

## Impact

- `evolution/campaigns/terminal-openspec-productization/campaign.toml`
- `packages/ethos/src/ethos/repository/adoption/evolution.py`
- campaign governance tests and canonical documentation
- a claim and dated Chronicle for this correction
