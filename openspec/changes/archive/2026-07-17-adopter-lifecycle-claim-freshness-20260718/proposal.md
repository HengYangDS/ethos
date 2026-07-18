## Why

The active adopter lifecycle claim currently hashes broad CLI directories. Unrelated root-reader or CLI test changes can therefore stale the claim even when universal adopter lifecycle behavior is unchanged, blocking otherwise unrelated governed work.

## What Changes

- Narrow the claim's semantic promotion targets to the two lifecycle command implementations and their exact adopter lifecycle regressions.
- Preserve fail-closed semantic-scope freshness: a change to either implementation or covered regression must stale the claim.
- Refresh the claim's dated Chronicle digest and record the exact scope migration under a formal OpenSpec Change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=adopter-lifecycle-claim-freshness; reuse=extend; change=modify; facet:lifecycle=evidence-freshness,validation; facet:surface=claims,chronicle,test,openspec; facet:authority=source,test,openspec,claim,evidence. Semantic-scope claim freshness SHALL bind a lifecycle claim to its actual implementation and behavioral regression surface rather than unrelated directory-wide paths.

## Impact

- `evidence/claims/adopter-openspec-lifecycle-20260714.toml`
- Its dated Chronicle and claim-freshness regression tests.
- The repository-governance specification.

## Out Of Scope

- Changing plan/prove lifecycle behavior, weakening semantic-scope freshness, changing generic claim-digest semantics, or editing foreign Work Lanes.
