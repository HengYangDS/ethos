## Why

ETHOS currently reports 100 percent coverage for public Python product-surface
Docstrings, while the policy floor still permits regression to 95 percent. That
is weaker than the current proven state and leaves a gap between achieved
quality and enforced quality.

## What Changes

- Raise `.config/checks/docstrings/policy.toml` `fail_under` from 95 to 100.
- Add architecture tests that make the 100 percent floor a release-surface
  contract rather than an incidental current metric.
- Clarify the quality specification so the public-surface docstring gate fails
  below the configured 100 percent floor.

## Capabilities

- `quality`: subject=docstring-floor-100; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=quality,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- No blanket requirement for every private helper to carry a docstring.
- No change to the non-blocking broader public-definition inventory.
- No new docstring parser or external dependency.
