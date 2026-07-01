---
subject: ethos:evidence:campaign-orchestration
claim: ethos-campaign-orchestration
date: 2026-07-02
role: evidence
state: active
relations:
  canonical_for: campaign orchestration evidence
---

# Campaign Orchestration Evidence

Purpose: record proof and judgment for the campaign orchestration Work Lane.

## Scope

This evidence binds the `ethos-campaign-orchestration` Work Lane. The lane adds
an ETHOS-native campaign manifest model so terminal OpenSpec productization can
run as an ordered campaign made of multiple OpenSpec-backed Work Lanes.

The campaign is not a giant Work Lane. It is a batch-level orchestration record
under `evolution/campaigns/<campaign-id>/campaign.toml`. Each campaign step
names its OpenSpec change, Work Lane branch, claim, closeout evidence refs, and
closeout state. Each step still proves, lands, closeout-applies, and retires as
its own Work Lane.

## Design Inputs

- `di-effect` informed capability-local profiles, direct routing, reuse stance,
  dynamic facets, live-spec diff guards, and archive normalization.
- `alphasim-dmgr-fix-b3` informed the portable campaign pattern: a read-only
  registry for long-running objectives, explicit carrier bindings, topic-scoped
  closeout evidence, Work Lane aware lifecycle state, and clear local-proof
  boundaries.
- ETHOS intentionally does not copy adopter-specific Backlog or Mission
  vocabulary. The product vocabulary remains campaign, OpenSpec change, Work
  Lane, claim, evidence, and closeout.

## RED Evidence

- Campaign manifest behavior was introduced test-first. The initial focused
  campaign tests failed because `ethos_repository.evolution` did not export
  `campaign_report`.
- After merging current `dev`, the existing closeout package test failed on
  stale assumptions that parity backlog and shadow parity packages must be
  empty or matched. The observed product state had six generic parity backlog
  entries and an alphasim shadow refresh package for the current product HEAD.
- The campaign closeout schema then rejected the real refresh package with
  `Additional properties are not allowed ('refresh_package' was unexpected)`.

## GREEN Evidence

Commands run from `/Users/yheng/projects/ethos-work-campaign-orchestration`:

```text
uv run --group dev pytest -q tests/unit/test_evolution_ledger.py::test_campaign_report_exposes_manifest_steps_and_closeout_progress tests/unit/test_cli_contracts.py::test_campaign_status_reports_manifest_steps tests/unit/test_cli_contracts.py::test_campaign_closeout_reports_local_campaign_packages tests/unit/test_schema_validation_and_gates.py::test_campaign_schema_accepts_lane_closeout_steps
```

Result: `4 passed in 0.29s`.

```text
uv run --package ethos ethos quality schemas --json
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`, `schema_count=37`,
`campaign.schema.json` valid, `campaign-closeout.schema.json` valid,
`campaign-contract` valid, and `campaign-closeout-contract` valid.

```text
uv run openspec validate --all --strict --json
```

Result: `10/10` OpenSpec items passed. The active
`ethos-campaign-orchestration` change passed strict validation.

```text
uv run --package ethos ethos campaign status --json
```

Result: `ok=true`, `state=active`, `required_gaps=[]`, with one active campaign
and nine ordered steps. The current campaign summary is `planned=8`,
`active=1`, `closed=0`.

```text
uv run --package ethos ethos campaign closeout --json
```

Result: `ok=true`, `state=local_ready`, `required_gaps=[]`,
`campaign_ok=true`, and campaign validation ready. The command exposes current
shadow parity state as `invalid` with a refresh package instead of hiding stale
adopter evidence.

## Claim Binding Verification

After creating `claims/ethos-campaign-orchestration.toml`, the following
commands were run from the Work Lane:

```text
uv run --package ethos ethos quality claims --json
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`. The new claim reported
`digest_trusted=true` for this evidence file and its OpenSpec carrier was
`openspec/changes/ethos-campaign-orchestration`.

```text
uv run --package ethos ethos quality schemas --json
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`, with
`campaign.schema.json`, `campaign-closeout.schema.json`, `campaign-contract`,
and `campaign-closeout-contract` all valid.

```text
uv run --group dev pytest -q tests/unit/test_evolution_ledger.py::test_campaign_report_exposes_manifest_steps_and_closeout_progress tests/unit/test_cli_contracts.py::test_campaign_status_reports_manifest_steps tests/unit/test_cli_contracts.py::test_campaign_closeout_reports_local_campaign_packages tests/unit/test_schema_validation_and_gates.py::test_campaign_schema_accepts_lane_closeout_steps
```

Result: `4 passed in 0.31s`.

## Parity Evidence Refresh

After syncing with current `dev`, tracked parity evidence for `generic` and
`alphasim-dmgr` pointed at an older product HEAD. The Work Lane refreshed both
tracked evidence files through the ETHOS command plane:

```text
uv run --package ethos ethos parity shadow --adopter generic --target /Users/yheng/projects/ethos-work-campaign-orchestration --execute --write-evidence --json
uv run --package ethos ethos parity shadow --adopter alphasim-dmgr --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --execute --write-evidence --json
```

Result: both returned `ok=true`, `state=matched`, `required_gaps=[]`.

```text
uv run --package ethos ethos parity gaps --json
uv run --package ethos ethos parity gaps --adopter alphasim-dmgr --json
```

Result: both returned `ok=true`, `state=clean`, `required_gaps=[]`,
`pending_count=0`.

## Boundaries

- This lane implements the campaign mechanism and records the terminal
  productization campaign manifest. It does not implement every later terminal
  productization lane.
- Planned future campaign steps are allowed to name intended OpenSpec changes
  before their carriers exist. Active, landed, closed, and retired steps must
  have active or archived OpenSpec carriers.
- The final accepted-root closeout and Work Lane retirement are command
  operations performed after this evidence is committed. The final response for
  this lane records those executed command results.

Status: see front matter.

See also: [Evolution Campaign](../governance/evolution-campaign.md), [Terminal Governance Product Design](../architecture/terminal-governance-product-design.md), and [OpenSpec Governance](../governance/openspec-governance.md).
