# report-coordination-required-risk

## Why

`ethos report --json` already exposes coordination advisories, but a future
status-required Work Lane coordination blocker must not disappear behind a green
scorecard. Report remains read-only; it should mirror required coordination gaps
from status without upgrading advisory coordination signals.

## What Changes

- Split report coordination risk into required and advisory buckets.
- Apply required coordination visibility across governed repository profiles.
- Include status-required coordination gaps in report `required_gaps` and
  `gap_layers.coordination_risk.required_gaps`.
- Keep advisory coordination signals advisory and non-authorizing.

## Impact

Humans and agents can see blocking coordination risk from the scorecard while
foreign Work Lane cleanup still requires owner handoff or maintainer policy.
