# Local CI Git Bundle Locale Robustness

## Why

The accepted HEAD's full local CI fallback reports `2231 passed, 1 failed` on a
Chinese-locale workstation. The failing test requires the English phrase
`complete history`, while Git reports the equivalent localized complete-history
message. This makes local proof depend on workstation language rather than
bundle correctness.

## What Changes

- Fix the message locale only for the exact `git bundle verify` assertion.
- Retain the zero-exit and complete-history semantic checks.
- Record the RED observation and governed local closeout evidence.

## Out Of Scope

- Product runtime behavior, bundle creation, handoff contracts, shared Git
  helpers, global test locale, remote publication, and foreign Work Lanes.

## Capabilities

- `quality`: subject=local-ci-git-bundle-locale-robustness; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=test,ci,evidence;
  facet:authority=test,openspec,evidence
