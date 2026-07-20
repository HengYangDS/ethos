## Why

The global source budget currently treats effective lines as a cross-language
currency. That measure is useful for individual-file readability, but it can be
reduced through formatting while semantic structure or payload grows. ETHOS
needs a metric-domain contract before changing enforcement, and the predecessor
blocked observation plus the successor's current campaign-terminal advisory and
debt facts must remain visible throughout migration.

## What Changes

- Accept the Budget Contract v2 architecture: typed carrier inventory,
  versioned native metrics, and a non-compensating budget vector.
- Preserve ELOC as the individual-file readability ceiling while planning the
  later retirement of repository-wide LOC enforcement.
- Freeze the v1 baseline, current observation, debt inventory, and known replay
  drift without resetting or converting them.
- Extract the existing v1 source-budget domain behavior from `domain/prove.py`
  into its own owner module without changing command JSON, exit status, policy,
  gate membership, campaign binding, or required/advisory-gap semantics for the
  same controlled inputs.
- Define the later replay, shadow, Debt v2, changed-scope admission, dual-control,
  cutover, rollback, and terminal-settlement sequence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=metric-domain-budget-contract; reuse=extend; change=modify; facet:lifecycle=validation,migration,rollback; facet:surface=contracts,schemas,source-budget; facet:authority=source,test,openspec,claim,evidence.
- `quality`: subject=budget-contract-v2-migration-integrity; reuse=extend; change=modify; facet:lifecycle=validation,proof,closeout; facet:surface=quality,report,openspec,evidence; facet:authority=source,test,openspec,claim,evidence.

## Impact

Affected surfaces are Decision Records, plans, OpenSpec contracts, claim and
Chronicle evidence, the source-budget domain owner, scorecard import, command
registry provider, campaign closeout consumer, and focused tests. This Change
does not alter v1 thresholds, debt dates, inventory classification rules, proof
scope, or enforcement.

## Out Of Scope

- Changing v1 enforcement, baseline, allowance, debt expiry, terminal targets, or inventory.
- Calibrating v2 thresholds, cutting authority over to v2, retiring global LOC, or claiming terminal compression completion.
- Remote publication, hosted CI success, or mutation/retirement of foreign Work Lanes.
